"""SQLite-backed users and password authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import Settings

SUPER_ADMIN = "super_admin"
MEMBER = "member"
SINGLE_USER_ID = "single-user"


class UserAlreadyExistsError(ValueError):
    """Raised when a username is already registered."""


class UserNotFoundError(LookupError):
    """Raised when a user does not exist."""


class ProtectedUserError(ValueError):
    """Raised when an operation would remove the only super admin."""


class UserRepository:
    """Stores users in the same SQLite file as application conversations."""

    def __init__(self, path: str | Path, settings: Settings) -> None:
        self.path = Path(path).expanduser()
        self.settings = settings
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('super_admin', 'member')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            existing = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if existing == 0:
                now = _now()
                connection.execute(
                    "INSERT INTO users(id, username, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        SINGLE_USER_ID,
                        self.settings.auth_username.strip(),
                        _hash_password(self.settings.auth_password),
                        SUPER_ADMIN,
                        now,
                        now,
                    ),
                )

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, username, password_hash, role, created_at, updated_at FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return _public_user(row)

    def get(self, user_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, username, role, created_at, updated_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return _public_user(row) if row else None

    def list_users(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, username, role, created_at, updated_at FROM users ORDER BY CASE role WHEN 'super_admin' THEN 0 ELSE 1 END, username COLLATE NOCASE"
            ).fetchall()
        return [_public_user(row) for row in rows]

    def create_member(self, username: str, password: str) -> dict[str, Any]:
        username = _validate_username(username)
        _validate_password(password)
        now = _now()
        record = {
            "id": str(uuid4()),
            "username": username,
            "password_hash": hash_password(password),
            "role": MEMBER,
            "created_at": now,
            "updated_at": now,
        }
        try:
            with self._connection() as connection:
                connection.execute(
                    "INSERT INTO users(id, username, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    tuple(record.values()),
                )
        except sqlite3.IntegrityError as error:
            raise UserAlreadyExistsError(username) from error
        return {key: value for key, value in record.items() if key != "password_hash"}

    def update_member(self, user_id: str, username: str | None, password: str | None) -> dict[str, Any]:
        if not username and not password:
            raise ValueError("至少提供用户名或密码。")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, username, role, created_at, updated_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                raise UserNotFoundError(user_id)
            if row["role"] != MEMBER:
                raise ProtectedUserError("超级管理员账号不能通过成员接口修改。")
            next_username = _validate_username(username) if username else row["username"]
            if password:
                _validate_password(password)
            try:
                connection.execute(
                    "UPDATE users SET username = ?, password_hash = COALESCE(?, password_hash), updated_at = ? WHERE id = ?",
                    (next_username, hash_password(password) if password else None, _now(), user_id),
                )
            except sqlite3.IntegrityError as error:
                raise UserAlreadyExistsError(next_username) from error
            updated = connection.execute(
                "SELECT id, username, role, created_at, updated_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return _public_user(updated)

    def delete_member(self, user_id: str) -> None:
        with self._connection() as connection:
            row = connection.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                raise UserNotFoundError(user_id)
            if row["role"] != MEMBER:
                raise ProtectedUserError("不能删除超级管理员账号。")
            connection.execute("DELETE FROM users WHERE id = ?", (user_id,))


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_username(username: str) -> str:
    value = username.strip()
    if not value or len(value) > 100:
        raise ValueError("用户名不能为空且不能超过 100 个字符。")
    return value


def _validate_password(password: str) -> None:
    if len(password) < 6 or len(password) > 256:
        raise ValueError("密码长度必须为 6 到 256 个字符。")


def hash_password(password: str) -> str:
    _validate_password(password)
    return _hash_password(password)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return "scrypt$16384$8$1${salt}${digest}".format(
        salt=base64.urlsafe_b64encode(salt).decode("ascii"),
        digest=base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_value, digest_value = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in ("id", "username", "role", "created_at", "updated_at")}
