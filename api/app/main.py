import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.deletion import router as account_deletion_router
from app.auth.router import router as auth_router
from app.bookings.availability import router as availability_router
from app.bookings.router import router as bookings_router
from app.catalogue.router import router as catalogue_router
from app.catalogue.saved import router as saved_router
from app.core.config import get_settings
from app.media.local_router import router as local_media_router
from app.media.router import router as media_router
from app.meetups.router import router as meetups_router
from app.memberships.router import router as memberships_router
from app.payments.router import router as payments_router
from app.profiles.router import router as profiles_router
from app.reviews.router import router as reviews_router
from app.schemas import HealthResponse
from app.transactions.release import run_local_sweep
from app.transactions.router import router as transactions_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    sweep = None
    if settings.local_release_sweep_seconds > 0:
        sweep = asyncio.create_task(run_local_sweep(settings.local_release_sweep_seconds))
    yield
    if sweep:
        sweep.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweep


app = FastAPI(
    title="PassIt API",
    summary="Contract-first API for the PassIt peer-to-peer rental prototype.",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, operation_id="getHealth", tags=["platform"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.environment)


app.include_router(auth_router, prefix="/v1")
app.include_router(account_deletion_router, prefix="/v1")
app.include_router(catalogue_router, prefix="/v1")
app.include_router(availability_router, prefix="/v1")
app.include_router(media_router, prefix="/v1")
app.include_router(local_media_router, prefix="/v1")
app.include_router(bookings_router, prefix="/v1")
app.include_router(memberships_router, prefix="/v1")
app.include_router(payments_router, prefix="/v1")
app.include_router(reviews_router, prefix="/v1")
app.include_router(transactions_router, prefix="/v1")

app.include_router(profiles_router, prefix="/v1")
app.include_router(saved_router, prefix="/v1")
app.include_router(meetups_router, prefix="/v1")
