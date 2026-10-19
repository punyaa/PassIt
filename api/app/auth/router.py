from fastapi import APIRouter
from pydantic import EmailStr

from app.core.stubs import not_implemented
from app.schemas import ApiModel

router = APIRouter(prefix="/auth", tags=["authentication"])


class SessionRequest(ApiModel):
    email: EmailStr
    password: str


class SessionResponse(ApiModel):
    user_id: str
    display_name: str


@router.post("/session", response_model=SessionResponse, operation_id="createSession")
async def create_session(_: SessionRequest) -> SessionResponse:
    not_implemented("JWT session issuance", "P1 Platform")
