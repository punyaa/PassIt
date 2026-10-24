from fastapi import APIRouter
from pydantic import EmailStr

from app.auth.dependencies import CurrentUser
from app.core.stubs import not_implemented
from app.schemas import ApiModel

router = APIRouter(prefix="/auth", tags=["authentication"])


class SessionRequest(ApiModel):
    email: EmailStr
    password: str


class SessionResponse(ApiModel):
    user_id: str
    display_name: str


class CurrentUserResponse(ApiModel):
    user_id: str
    display_name: str
    email: str


@router.post("/session", response_model=SessionResponse, operation_id="createSession")
async def create_session(_: SessionRequest) -> SessionResponse:
    not_implemented("JWT session issuance", "P1 Platform")


@router.get("/me", response_model=CurrentUserResponse, operation_id="getCurrentUser")
async def get_current_user(user: CurrentUser) -> CurrentUserResponse:
    """Who the session belongs to. 401 when signed out."""
    return CurrentUserResponse(
        user_id=str(user.id), display_name=user.display_name, email=user.email
    )
