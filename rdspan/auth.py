from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from rdspan import config

COOKIE = "rdspan_session"
OPEN_PATHS = {"/healthz"}


def _secret() -> bytes:
    return (config.basic_auth_pass() + "|rdspan").encode("utf-8")


def sign_user(username: str) -> str:
    digest = hmac.new(_secret(), username.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{username}.{digest}"


def verify_session(token: str) -> str | None:
    if "." not in token:
        return None
    username, _, digest = token.rpartition(".")
    expected = hmac.new(_secret(), username.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(digest, expected):
        return None
    if not secrets.compare_digest(
        username.encode("utf-8"), config.basic_auth_user().encode("utf-8")
    ):
        return None
    return username


def user_from_basic(header: str) -> str | None:
    if not header.lower().startswith("basic "):
        return None
    try:
        raw = base64.b64decode(header.split(" ", 1)[1].strip()).decode("utf-8")
    except Exception:
        return None
    username, sep, password = raw.partition(":")
    if not sep:
        return None
    user_ok = secrets.compare_digest(
        username.encode("utf-8"), config.basic_auth_user().encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        password.encode("utf-8"), config.basic_auth_pass().encode("utf-8")
    )
    if user_ok and pass_ok:
        return username
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in OPEN_PATHS:
            return await call_next(request)

        user = verify_session(request.cookies.get(COOKIE, ""))
        if user is None:
            user = user_from_basic(request.headers.get("authorization", ""))
        if user is None:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="rdspan"'},
                content="Authentication required",
                media_type="text/plain",
            )

        request.state.username = user
        response = await call_next(request)
        response.set_cookie(
            COOKIE,
            sign_user(user),
            httponly=True,
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24 * 30,
        )
        return response
