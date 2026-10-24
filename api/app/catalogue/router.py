from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import Field, model_validator
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.catalogue.mrt_stations import STATIONS_BY_NAME, nearest_station
from app.catalogue.price_suggestion import suggest_price
from app.core.config import get_settings
from app.core.db import DbSession
from app.integrations.onemap import geocode_postal_code
from app.media.service import attach_media, listing_photo_urls
from app.models import Availability, Booking, Review, User, inclusive_range
from app.models import Listing as ListingRow
from app.schemas import ApiModel, DateWindow

router = APIRouter(prefix="/listings", tags=["catalogue"])

ListingStatus = Literal["active", "paused", "archived"]
BLOCKING_STATES = ("confirmed", "handed_over")
Price = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


class Listing(ApiModel):
    """Public listing card. Location is the nearest MRT station and planning area only;
    exact addresses and postal codes are never stored or exposed."""

    id: UUID
    owner_id: UUID
    title: str
    description: str | None = None
    category: str
    condition: str
    price_day: Decimal
    price_week: Decimal | None = None
    price_month: Decimal | None = None
    deposit: Decimal
    mrt_station: str | None = None
    planning_area: str | None = None
    status: ListingStatus
    photo_urls: list[str] = []


class ListingDetail(Listing):
    owner_display_name: str
    owner_rating: float | None = None
    owner_review_count: int = 0


class ListingCreate(ApiModel):
    title: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(min_length=2, max_length=60)
    condition: str = Field(min_length=2, max_length=30)
    price_day: Price
    price_week: Price | None = None
    price_month: Price | None = None
    deposit: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
    postal_code: str | None = Field(default=None, pattern=r"^\d{6}$")
    mrt_station: str | None = Field(
        default=None, description="Used when no postal code is given or geocoding fails."
    )
    photo_keys: list[str] = Field(default_factory=list, max_length=10)
    availability: list[DateWindow] | None = Field(
        default=None, description="Open windows. Defaults to the next 365 days."
    )

    @model_validator(mode="after")
    def has_location(self) -> "ListingCreate":
        if not self.postal_code and not self.mrt_station:
            raise ValueError("Provide a postal_code or an mrt_station")
        return self


class ListingUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    condition: str | None = Field(default=None, min_length=2, max_length=30)
    price_day: Price | None = None
    price_week: Price | None = None
    price_month: Price | None = None
    deposit: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)] | None = None
    status: ListingStatus | None = None


class PriceSuggestionRequest(ApiModel):
    title: str = Field(min_length=3, max_length=120)
    category: str
    condition: str


class PriceBand(ApiModel):
    min: Decimal
    recommended: Decimal
    max: Decimal


class PriceSuggestion(ApiModel):
    day: PriceBand
    week: PriceBand
    month: PriceBand
    source: Literal["llm", "heuristic", "cache"]


class MrtStation(ApiModel):
    name: str
    planning_area: str


def _to_card(listing: ListingRow, photos: list[str]) -> Listing:
    return Listing(
        id=listing.id,
        owner_id=listing.owner_id,
        title=listing.title,
        description=listing.description,
        category=listing.category,
        condition=listing.condition,
        price_day=listing.price_day,
        price_week=listing.price_week,
        price_month=listing.price_month,
        deposit=listing.deposit,
        mrt_station=listing.mrt_station,
        planning_area=listing.planning_area,
        status=listing.status,
        photo_urls=photos,
    )


async def _cards(db: AsyncSession, listings: list[ListingRow]) -> list[Listing]:
    photos = await listing_photo_urls(db, [listing.id for listing in listings])
    return [_to_card(listing, photos.get(listing.id, [])) for listing in listings]


def free_dates_clause(start: date, end: date):  # noqa: ANN201 - SQLAlchemy expression
    """Listings open for the whole of [start, end] with no blocking booking."""
    requested = inclusive_range(start, end)
    return and_(
        exists().where(
            Availability.listing_id == ListingRow.id, Availability.period.contains(requested)
        ),
        ~exists().where(
            Booking.listing_id == ListingRow.id,
            Booking.state.in_(BLOCKING_STATES),
            Booking.period.overlaps(requested),
        ),
    )


@router.get("", response_model=list[Listing], operation_id="listListings")
async def list_listings(
    db: DbSession,
    q: str | None = None,
    category: str | None = None,
    mrt: str | None = None,
    planning_area: str | None = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Listing]:
    """Search active listings. `from`/`to` keep only listings free for the whole range."""
    query = select(ListingRow).where(ListingRow.status == "active")
    if q:
        document = func.to_tsvector("english", ListingRow.title + " " + ListingRow.category)
        query = query.where(
            or_(
                document.op("@@")(func.plainto_tsquery("english", q)),
                ListingRow.title.ilike(f"%{q}%"),
            )
        )
    if category:
        query = query.where(ListingRow.category == category)
    if mrt:
        query = query.where(func.lower(ListingRow.mrt_station) == mrt.lower())
    if planning_area:
        query = query.where(func.lower(ListingRow.planning_area) == planning_area.lower())
    if min_price is not None:
        query = query.where(ListingRow.price_day >= min_price)
    if max_price is not None:
        query = query.where(ListingRow.price_day <= max_price)
    if from_date or to_date:
        start, end = from_date or to_date, to_date or from_date
        if end < start:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "`to` must not be before `from`")
        query = query.where(free_dates_clause(start, end))
    query = query.order_by(ListingRow.created_at.desc(), ListingRow.id).limit(limit).offset(offset)
    return await _cards(db, list(await db.scalars(query)))


@router.get("/mine", response_model=list[Listing], operation_id="listMyListings")
async def list_my_listings(user: CurrentUser, db: DbSession) -> list[Listing]:
    listings = await db.scalars(
        select(ListingRow)
        .where(ListingRow.owner_id == user.id)
        .order_by(ListingRow.created_at.desc(), ListingRow.id)
    )
    return await _cards(db, list(listings))


@router.get("/mrt-stations", response_model=list[MrtStation], operation_id="listMrtStations")
async def list_mrt_stations() -> list[MrtStation]:
    """Stations available for the location filter and the listing-form fallback."""
    return [
        MrtStation(name=station.name, planning_area=station.planning_area)
        for station in STATIONS_BY_NAME.values()
    ]


async def _require_listing_slot(db: AsyncSession, owner_id: UUID) -> None:
    """Free tier: at most `free_listing_limit` non-archived listings per lender. The user
    row lock serialises concurrent creates by the same lender."""
    await db.execute(select(User.id).where(User.id == owner_id).with_for_update())
    count = await db.scalar(
        select(func.count()).where(ListingRow.owner_id == owner_id, ListingRow.status != "archived")
    )
    limit = get_settings().free_listing_limit
    if count >= limit:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Free accounts can have {limit} listings. Archive one to add another.",
        )


async def _locate(request: ListingCreate) -> tuple[float, float, str, str]:
    """Return (latitude, longitude, mrt_station, planning_area)."""
    if request.postal_code:
        geocoded = await geocode_postal_code(request.postal_code)
        if geocoded:
            station = nearest_station(geocoded.latitude, geocoded.longitude)
            area = geocoded.planning_area or station.planning_area
            return geocoded.latitude, geocoded.longitude, station.name, area
    if request.mrt_station:
        station = STATIONS_BY_NAME.get(request.mrt_station.strip().lower())
        if station:
            return station.latitude, station.longitude, station.name, station.planning_area
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Could not locate that postal code. Choose your nearest MRT station instead.",
    )


@router.post(
    "",
    response_model=ListingDetail,
    status_code=status.HTTP_201_CREATED,
    operation_id="createListing",
)
async def create_listing(request: ListingCreate, user: CurrentUser, db: DbSession) -> ListingDetail:
    latitude, longitude, station, area = await _locate(request)
    await _require_listing_slot(db, user.id)
    listing = ListingRow(
        owner_id=user.id,
        title=request.title.strip(),
        description=request.description,
        category=request.category.strip(),
        condition=request.condition.strip(),
        price_day=request.price_day,
        price_week=request.price_week,
        price_month=request.price_month,
        deposit=request.deposit,
        latitude=latitude,
        longitude=longitude,
        mrt_station=station,
        planning_area=area,
        status="active",
    )
    db.add(listing)
    await db.flush()
    windows = request.availability or [
        DateWindow(start_date=date.today(), end_date=date.today() + timedelta(days=365))
    ]
    db.add_all(
        Availability(listing_id=listing.id, period=inclusive_range(w.start_date, w.end_date))
        for w in windows
    )
    await attach_media(db, request.photo_keys, "listing", user.id, listing_id=listing.id)
    await db.commit()
    return await _detail(db, listing)


@router.post(
    "/price-suggestion", response_model=PriceSuggestion, operation_id="suggestListingPrice"
)
async def suggest_listing_price(
    request: PriceSuggestionRequest, _: CurrentUser, db: DbSession
) -> PriceSuggestion:
    """Suggest day/week/month prices before the listing exists. Falls back to a
    median-based heuristic whenever the model is unavailable, slow or invalid."""
    prices, source = await suggest_price(db, request.title, request.category, request.condition)
    return PriceSuggestion(**prices, source=source)


async def _detail(db: AsyncSession, listing: ListingRow) -> ListingDetail:
    owner = await db.get(User, listing.owner_id)
    rating, count = (
        await db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.target_id == listing.owner_id
            )
        )
    ).one()
    [card] = await _cards(db, [listing])
    return ListingDetail(
        **card.model_dump(),
        owner_display_name=owner.display_name,
        owner_rating=round(float(rating), 2) if rating is not None else None,
        owner_review_count=count,
    )


@router.get("/{listing_id}", response_model=ListingDetail, operation_id="getListing")
async def get_listing(listing_id: UUID, db: DbSession) -> ListingDetail:
    listing = await db.get(ListingRow, listing_id)
    if listing is None or listing.status == "archived":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return await _detail(db, listing)


@router.patch("/{listing_id}", response_model=ListingDetail, operation_id="updateListing")
async def update_listing(
    listing_id: UUID, request: ListingUpdate, user: CurrentUser, db: DbSession
) -> ListingDetail:
    listing = await db.get(ListingRow, listing_id)
    if listing is None or listing.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    changes = request.model_dump(exclude_unset=True)
    if listing.status == "archived" and changes.get("status") in ("active", "paused"):
        await _require_listing_slot(db, user.id)
    for field, value in changes.items():
        if value is None and field in {"title", "condition", "price_day", "deposit", "status"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field} cannot be cleared")
        setattr(listing, field, value)
    await db.commit()
    return await _detail(db, listing)
