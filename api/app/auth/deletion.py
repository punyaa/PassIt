"""Account deletion: erase the person, keep the transactions.

Other people's bookings, ledger entries, reviews and condition evidence point at the user row,
so it is anonymised rather than removed:

  - email, password, name, bio and avatar are wiped; the email becomes an unusable
    `deleted-<id>@deleted.invalid` (the `.invalid` domain can never receive mail or sign up),
    so the real address is free to register again;
  - listings never rented are deleted with their photos and dates; listings with rental history
    are archived and stripped of description, photos, open dates and coordinates;
  - the person's saved listings are removed, and their open or upcoming meetups cancelled;
  - bookings, ledger entries, checklists and reviews stay, now attributed to "Deleted user".

Deletion is refused while any rental is still in progress (as borrower or lender), so nobody's
fee or deposit is left mid-flow. Existing sessions stop working at once because
`current_user` rejects accounts with `deleted_at` set.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import Field
from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import SESSION_COOKIE, CurrentUser
from app.auth.passwords import verify_password
from app.core.db import DbSession
from app.meetups.router import cancel_open_meetups
from app.models import Availability, Booking, Listing, Media, SavedListing, User
from app.schemas import ApiModel

router = APIRouter(prefix="/auth", tags=["authentication"])

DELETED_NAME = "Deleted user"
# Anything not finished: fees or deposits could still move, or the other party still needs us.
OPEN_STATES = ("requested", "confirmed", "handed_over", "returned", "disputed")


class AccountDeletionPreview(ApiModel):
    """What deleting the account would do right now."""

    allowed: bool
    open_rentals: int = Field(description="Rentals still in progress; they block deletion.")
    listings_deleted: int = Field(description="Listings never rented: deleted for good.")
    listings_archived: int = Field(description="Listings with rental history: archived, scrubbed.")


class AccountDeletionRequest(ApiModel):
    password: str = Field(min_length=1, max_length=128)


async def _open_rentals(db: AsyncSession, user_id) -> int:  # noqa: ANN001 - UUID
    return await db.scalar(
        select(func.count())
        .select_from(Booking)
        .join(Listing, Listing.id == Booking.listing_id)
        .where(
            or_(Booking.borrower_id == user_id, Listing.owner_id == user_id),
            Booking.state.in_(OPEN_STATES),
        )
    )


async def _listings_by_history(db: AsyncSession, user_id) -> tuple[list[Listing], list[Listing]]:  # noqa: ANN001
    """(never rented, rented before) among the user's listings."""
    listings = list(await db.scalars(select(Listing).where(Listing.owner_id == user_id)))
    rented: list[Listing] = []
    never: list[Listing] = []
    for listing in listings:
        has_history = await db.scalar(select(exists().where(Booking.listing_id == listing.id)))
        (rented if has_history else never).append(listing)
    return never, rented


@router.get(
    "/me/deletion", response_model=AccountDeletionPreview, operation_id="previewAccountDeletion"
)
async def preview_account_deletion(user: CurrentUser, db: DbSession) -> AccountDeletionPreview:
    """Tell the person exactly what deleting their account would do, before they confirm."""
    open_rentals = await _open_rentals(db, user.id)
    never, rented = await _listings_by_history(db, user.id)
    return AccountDeletionPreview(
        allowed=open_rentals == 0,
        open_rentals=open_rentals,
        listings_deleted=len(never),
        listings_archived=len(rented),
    )


@router.post(
    "/me/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteAccount",
    responses={
        403: {"description": "Wrong password"},
        409: {"description": "Rentals still in progress"},
    },
)
async def delete_account(
    request: AccountDeletionRequest, user: CurrentUser, db: DbSession, response: Response
) -> None:
    """Permanently delete the account. Requires the current password."""
    me = await db.scalar(select(User).where(User.id == user.id).with_for_update())
    if not verify_password(request.password, me.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Incorrect password")
    if await _open_rentals(db, me.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You have rentals in progress. Finish or cancel them before deleting your account.",
        )

    never, rented = await _listings_by_history(db, me.id)
    for listing in never + rented:
        # Listing photos are the person's content; rental evidence (handover/return) is kept.
        await db.execute(
            delete(Media).where(Media.listing_id == listing.id, Media.stage == "listing")
        )
    for listing in never:
        await db.delete(listing)  # availability and others' saves cascade
    for listing in rented:
        listing.status = "archived"
        listing.description = None
        listing.latitude = listing.longitude = None
        await db.execute(delete(Availability).where(Availability.listing_id == listing.id))
    await db.execute(delete(SavedListing).where(SavedListing.user_id == me.id))
    await cancel_open_meetups(db, me.id, "Account deleted")

    me.email = f"deleted-{me.id}@deleted.invalid"
    me.password_hash = "!deleted"  # not an argon2 hash, so no password can ever match
    me.display_name = DELETED_NAME
    me.bio = None
    me.avatar_key = None
    me.deleted_at = datetime.now(UTC)
    await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
