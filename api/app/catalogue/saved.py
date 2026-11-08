"""Account-scoped bookmarks; saving and removal are idempotent."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.auth.dependencies import CurrentUser
from app.catalogue.router import Listing, _cards
from app.core.db import DbSession
from app.models import Listing as ListingRow
from app.models import SavedListing

router = APIRouter(prefix="/saved-listings", tags=["catalogue"])


@router.get("", response_model=list[Listing], operation_id="listSavedListings")
async def list_saved_listings(user: CurrentUser, db: DbSession) -> list[Listing]:
    rows = await db.scalars(
        select(ListingRow)
        .join(SavedListing)
        .where(SavedListing.user_id == user.id)
        .order_by(SavedListing.created_at.desc(), ListingRow.id)
    )
    return await _cards(db, list(rows))


@router.put("/{listing_id}", status_code=204, operation_id="saveListing")
async def save_listing(listing_id: UUID, user: CurrentUser, db: DbSession) -> Response:
    listing = await db.get(ListingRow, listing_id)
    if listing is None or listing.status != "active":
        raise HTTPException(404, "Listing is no longer available")
    await db.execute(
        insert(SavedListing).values(user_id=user.id, listing_id=listing_id).on_conflict_do_nothing()
    )
    await db.commit()
    return Response(status_code=204)


@router.delete("/{listing_id}", status_code=204, operation_id="unsaveListing")
async def unsave_listing(listing_id: UUID, user: CurrentUser, db: DbSession) -> Response:
    await db.execute(
        delete(SavedListing).where(
            SavedListing.user_id == user.id, SavedListing.listing_id == listing_id
        )
    )
    await db.commit()
    return Response(status_code=204)
