from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import SESSION_COOKIE, CurrentUser, issue_access_token
from app.auth.passwords import hash_password, verify_password
from app.core.config import get_settings
from app.core.db import DbSession
from app.models import User
from app.schemas import ApiModel

router = APIRouter(prefix="/auth", tags=["authentication"])

SESSION_TTL = timedelta(hours=12)


class SessionRequest(ApiModel):
    email: EmailStr
    password: str


class SignupRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class SessionResponse(ApiModel):
    user_id: str
    display_name: str


class CurrentUserResponse(ApiModel):
    user_id: str
    display_name: str
    email: str


def _normalise(email: str) -> str:
    return email.strip().lower()


def _start_session(response: Response, user: User) -> SessionResponse:
    """Issue the JWT as an httpOnly cookie, so scripts in the page can never read it."""
    response.set_cookie(
        SESSION_COOKIE,
        issue_access_token(user.id, SESSION_TTL),
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=get_settings().session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return SessionResponse(user_id=str(user.id), display_name=user.display_name)


@router.post(
    "/signup",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAccount",
)
async def create_account(
    payload: SignupRequest, response: Response, db: DbSession
) -> SessionResponse:
    user = User(
        email=_normalise(payload.email),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from error
    return _start_session(response, user)


@router.post("/session", response_model=SessionResponse, operation_id="createSession")
async def create_session(
    payload: SessionRequest, response: Response, db: DbSession
) -> SessionResponse:
    user = await db.scalar(select(User).where(User.email == _normalise(payload.email)))
    # Always verify, even for unknown emails, so the two failure cases are indistinguishable.
    valid = verify_password(payload.password, user.password_hash if user else None)
    if user is None or not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return _start_session(response, user)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteSession")
async def delete_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=CurrentUserResponse, operation_id="getCurrentUser")
async def get_current_user(user: CurrentUser) -> CurrentUserResponse:
    """Who the session belongs to. 401 when signed out."""
    return CurrentUserResponse(
        user_id=str(user.id), display_name=user.display_name, email=user.email
    )
