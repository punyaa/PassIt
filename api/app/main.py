from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.bookings.router import router as bookings_router
from app.catalogue.router import router as catalogue_router
from app.core.config import get_settings
from app.media.router import router as media_router
from app.reviews.router import router as reviews_router
from app.schemas import HealthResponse
from app.transactions.router import router as transactions_router

settings = get_settings()

app = FastAPI(
    title="PassIt API",
    summary="Contract-first API for the PassIt peer-to-peer rental prototype.",
    version="0.1.0",
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
app.include_router(catalogue_router, prefix="/v1")
app.include_router(media_router, prefix="/v1")
app.include_router(bookings_router, prefix="/v1")
app.include_router(reviews_router, prefix="/v1")
app.include_router(transactions_router, prefix="/v1")
