"""Caller identity for the domain routers.

INTERIM (P1 Platform owns the final version). B1-B3 endpoints only depend on
`current_user` returning a `User`. P1 can replace the body of `current_user` -- for
example to add refresh tokens or Cognito -- without touching any domain router.

Contract the domain code relies on:
  - A JWT in `Authorization: Bearer <token>` or the `passit_session` httpOnly cookie.
  - HS256 signed with PASSIT_JWT_SECRET; `sub` is the user's UUID.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.db import DbSession
from app.models import User

SESSION_COOKIE = "passit_session"
bearer = HTTPBearer(auto_error=False)


def issue_access_token(user_id: UUID, ttl: timedelta = timedelta(hours=12)) -> str:
    """Sign a session token. Used by seed and load-test scripts until P1 ships login."""
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {"sub": str(user_id), "iat": now, "exp": now + ttl}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _user_id_from_token(token: str) -> UUID:
    settings = get_settings()
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session") from error


async def current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    token = credentials.credentials if credentials else session_cookie
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    user = await db.get(User, _user_id_from_token(token))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
