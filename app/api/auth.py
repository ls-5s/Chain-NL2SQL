"""Cookie sessions and role-protected member management."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth.repository import (
    SUPER_ADMIN,
    ProtectedUserError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserRepository,
)
from app.config.settings import Settings, get_settings
from app.schemas.request import LoginRequest, MemberCreateRequest, MemberUpdateRequest
from app.schemas.response import MemberResponse, SessionResponse

SESSION_COOKIE = "chain_nl2sql_session"
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
members_router = APIRouter(prefix="/api/v1/members", tags=["members"])
_repositories: dict[str, UserRepository] = {}
_repository_lock = Lock()


def get_user_repository(settings: Settings = Depends(get_settings)) -> UserRepository:
    path = str(settings.conversation_database_path)
    with _repository_lock:
        repository = _repositories.get(path)
        if repository is None:
            repository = UserRepository(path, settings)
            _repositories[path] = repository
        return repository


def get_current_user(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    user = _authenticated_user(request, settings)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    return user


def require_authenticated(request: Request, settings: Settings | None = None) -> str:
    user = _authenticated_user(request, settings or get_settings())
    return user["id"]


def require_super_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] != SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有超级管理员可以管理成员。")
    return user


@auth_router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, settings: Settings = Depends(get_settings), repository: UserRepository = Depends(get_user_repository)) -> SessionResponse:
    user = repository.authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码不正确。")
    response.set_cookie(SESSION_COOKIE, _make_session(settings, user), max_age=settings.session_max_age_seconds, httponly=True, samesite="lax", secure=settings.app_env != "local", path="/")
    return SessionResponse(authenticated=True, username=user["username"], role=user["role"])


@auth_router.post("/logout", response_model=SessionResponse)
def logout(response: Response) -> SessionResponse:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return SessionResponse(authenticated=False)


@auth_router.get("/session", response_model=SessionResponse)
def session(request: Request, settings: Settings = Depends(get_settings)) -> SessionResponse:
    user = _session_user(request, settings)
    return SessionResponse(authenticated=user is not None, username=user["username"] if user else None, role=user["role"] if user else None)


@members_router.get("", response_model=list[MemberResponse])
def list_members(repository: UserRepository = Depends(get_user_repository), _: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    return repository.list_users()


@members_router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(payload: MemberCreateRequest, repository: UserRepository = Depends(get_user_repository), _: dict[str, Any] = Depends(require_super_admin)) -> dict[str, Any]:
    try:
        return repository.create_member(payload.username, payload.password)
    except UserAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在。") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@members_router.patch("/{user_id}", response_model=MemberResponse)
def update_member(user_id: str, payload: MemberUpdateRequest, repository: UserRepository = Depends(get_user_repository), _: dict[str, Any] = Depends(require_super_admin)) -> dict[str, Any]:
    try:
        return repository.update_member(user_id, payload.username, payload.password)
    except UserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在。") from error
    except UserAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在。") from error
    except ProtectedUserError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@members_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(user_id: str, repository: UserRepository = Depends(get_user_repository), _: dict[str, Any] = Depends(require_super_admin)) -> None:
    try:
        repository.delete_member(user_id)
    except UserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在。") from error
    except ProtectedUserError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


def _make_session(settings: Settings, user: dict[str, Any]) -> str:
    payload = json.dumps({"user_id": user["id"], "username": user["username"], "expires_at": int(time.time()) + settings.session_max_age_seconds}, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(settings.session_secret.encode(), encoded, hashlib.sha256).hexdigest().encode()
    return f"{encoded.decode()}.{signature.decode()}"


def _session_user(request: Request, settings: Settings) -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or "." not in token:
        return None
    encoded, supplied_signature = token.rsplit(".", 1)
    expected_signature = hmac.new(settings.session_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        expires_at = int(payload.get("expires_at", 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if expires_at < int(time.time()) or not isinstance(payload.get("user_id"), str):
        return None
    user = get_user_repository(settings).get(payload["user_id"])
    return user if user and user["username"] == payload.get("username") else None


def _authenticated_user(request: Request, settings: Settings) -> dict[str, Any]:
    user = _session_user(request, settings)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    return user
