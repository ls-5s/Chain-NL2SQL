"""Single-account session authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.config.settings import Settings, get_settings
from app.schemas.request import LoginRequest
from app.schemas.response import SessionResponse

SINGLE_USER_ID = "single-user"
SESSION_COOKIE = "chain_nl2sql_session"

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def require_authenticated(request: Request) -> str:
    if _session_username(request, get_settings()) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")
    return SINGLE_USER_ID


@auth_router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, settings: Settings = Depends(get_settings)) -> SessionResponse:
    valid_username = hmac.compare_digest(payload.username.strip(), settings.auth_username)
    valid_password = hmac.compare_digest(payload.password, settings.auth_password)
    if not (valid_username and valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码不正确。")
    response.set_cookie(
        SESSION_COOKIE,
        _make_session(settings),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "local",
        path="/",
    )
    return SessionResponse(authenticated=True, username=settings.auth_username)


@auth_router.post("/logout", response_model=SessionResponse)
def logout(response: Response) -> SessionResponse:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return SessionResponse(authenticated=False)


@auth_router.get("/session", response_model=SessionResponse)
def session(request: Request, settings: Settings = Depends(get_settings)) -> SessionResponse:
    username = _session_username(request, settings)
    return SessionResponse(authenticated=username is not None, username=username)


def _make_session(settings: Settings) -> str:
    payload = json.dumps(
        {"user_id": SINGLE_USER_ID, "username": settings.auth_username, "expires_at": int(time.time()) + settings.session_max_age_seconds},
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(settings.session_secret.encode(), encoded, hashlib.sha256).hexdigest().encode()
    return f"{encoded.decode()}.{signature.decode()}"


def _session_username(request: Request, settings: Settings) -> str | None:
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
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("user_id") != SINGLE_USER_ID or payload.get("username") != settings.auth_username:
        return None
    return settings.auth_username if int(payload.get("expires_at", 0)) >= int(time.time()) else None
