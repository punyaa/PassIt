from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.stubs import not_implemented
from app.schemas import ApiModel

router = APIRouter(prefix="/listings", tags=["catalogue"])


class Listing(ApiModel):
    id: UUID
    title: str
    category: str
    condition: str
    price_day: Decimal
    price_week: Decimal | None = None
    price_month: Decimal | None = None
    deposit: Decimal
    mrt_station: str | None = None
    planning_area: str | None = None


class ListingCreate(ApiModel):
    title: str
    category: str
    condition: str
    price_day: Decimal
    price_week: Decimal | None = None
    price_month: Decimal | None = None
    deposit: Decimal
    postal_code: str


class AvailabilityResponse(ApiModel):
    listing_id: UUID
    from_date: date
    to_date: date
    available: bool


class PriceBand(ApiModel):
    min: Decimal
    recommended: Decimal
    max: Decimal


class PriceSuggestion(ApiModel):
    day: PriceBand
    week: PriceBand
    month: PriceBand
    source: str


@router.get("", response_model=list[Listing], operation_id="listListings")
async def list_listings(
    q: str | None = None,
    mrt: str | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> list[Listing]:
    del q, mrt, from_date, to_date
    return []


@router.post("", response_model=Listing, operation_id="createListing")
async def create_listing(_: ListingCreate) -> Listing:
    not_implemented("listing persistence and geocoding", "B3 Catalogue")


@router.get(
    "/{listing_id}/availability",
    response_model=AvailabilityResponse,
    operation_id="getListingAvailability",
)
async def get_listing_availability(
    listing_id: UUID,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> AvailabilityResponse:
    not_implemented(
        f"availability for {listing_id} from {from_date} to {to_date}", "B1 Booking"
    )


@router.post(
    "/{listing_id}/price-suggestion",
    response_model=PriceSuggestion,
    operation_id="suggestListingPrice",
)
async def suggest_listing_price(listing_id: UUID) -> PriceSuggestion:
    not_implemented(f"price suggestion for {listing_id}", "B3 Catalogue")
