"use client";

import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";

import { ListingPhoto } from "@/components/listing-card";
import { useSession } from "@/components/session";
import { Alert, Badge, Button, Card, Spinner } from "@/components/ui";
import { apiRequest, type Schemas } from "@/lib/api-client";
import { money } from "@/lib/format";
import { useApi } from "@/lib/use-api";

import { BookingPanel } from "./booking-panel";

export function ListingView({ id }: { id: string }) {
  const listing = useApi<Schemas["ListingDetail"]>(`/listings/${id}`);
  const { user } = useSession();
  const back = useSearchParams().get("back");
  const searchHref =
    back === "/search" || back?.startsWith("/search?") ? back : "/search";

  if (listing.loading) return <Spinner label="Loading listing…" />;
  if (listing.error || !listing.data) {
    return (
      <Alert
        title={
          listing.error?.status === 404
            ? "This listing isn't available"
            : "Couldn't load this listing"
        }
      >
        {listing.error?.status === 404 ? (
          <Link className="underline" href="/search">
            Browse other rentals
          </Link>
        ) : (
          listing.error?.message
        )}
      </Alert>
    );
  }

  const item = listing.data;
  const isOwner = user?.user_id === item.owner_id;

  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_380px]">
      <div>
        <Link className="text-sm font-bold text-muted" href={searchHref}>
          ← Back to search
        </Link>
        <Gallery listing={item} />
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Badge>{item.category}</Badge>
          <Badge tone="success">{item.condition}</Badge>
          {item.status !== "active" && (
            <Badge tone="warning">{item.status}</Badge>
          )}
        </div>
        <h1 className="mt-4 text-3xl font-extrabold sm:text-4xl tracking-[-0.045em]">
          {item.title}
        </h1>
        <p className="mt-2 text-muted">
          📍 Near {item.mrt_station ?? "—"} MRT ·{" "}
          {item.planning_area ?? "Singapore"}
        </p>
        <p className="mt-4 text-2xl font-extrabold">
          {money(item.price_day)}{" "}
          <span className="text-sm font-normal text-muted">/ day</span>
        </p>
        {item.description && (
          <p className="mt-6 whitespace-pre-line leading-7">
            {item.description}
          </p>
        )}

        <div className="mt-8 grid gap-3 sm:grid-cols-4">
          <Price label="Per day" value={item.price_day} />
          <Price label="Per week" value={item.price_week} />
          <Price label="Per month" value={item.price_month} />
          <Price label="Refundable deposit" value={item.deposit} />
        </div>

        <Card className="mt-8">
          <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-muted">
            Lender
          </p>
          <div className="mt-3 flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-full bg-sage font-extrabold">
              {item.owner_display_name.slice(0, 1)}
            </span>
            <div>
              <strong>{item.owner_display_name}</strong>
              <p className="text-sm text-muted">
                {item.owner_rating
                  ? `★ ${item.owner_rating.toFixed(1)} from ${item.owner_review_count} review${item.owner_review_count === 1 ? "" : "s"}`
                  : "No reviews yet"}
              </p>
            </div>
          </div>
          <Reviews userId={item.owner_id} />
        </Card>
        <p className="mt-6 text-xs leading-5 text-muted">
          Exact addresses are never shown. You arrange the pickup point with the
          lender after booking.
        </p>
      </div>

      <aside
        id="booking-details"
        className="scroll-mt-24 lg:sticky lg:top-28 lg:h-fit"
      >
        {isOwner ? (
          <OwnerPanel listing={item} onChange={listing.setData} />
        ) : (
          <BookingPanel listing={item} />
        )}
      </aside>
      {!isOwner && (
        <a className="mobile-booking-link" href="#booking-details">
          <span>
            {money(item.price_day)} <small>/ day</small>
          </span>
          <span>Choose dates →</span>
        </a>
      )}
    </div>
  );
}

function Gallery({ listing }: { listing: Schemas["ListingDetail"] }) {
  const [index, setIndex] = useState(0);
  const photos = listing.photo_urls ?? [];
  if (photos.length <= 1) {
    return (
      <div className="mt-4 overflow-hidden rounded-card">
        <ListingPhoto
          className="aspect-[4/3] sm:aspect-[3/2]"
          listing={listing}
        />
      </div>
    );
  }
  return (
    <div className="mt-4">
      <img
        alt={`${listing.title}, photo ${index + 1}`}
        className="aspect-[4/3] w-full rounded-card object-cover sm:aspect-[3/2]"
        src={photos[index]}
      />
      <div className="mt-3 flex gap-2 overflow-x-auto">
        {photos.map((url, i) => (
          <button
            aria-label={`Show photo ${i + 1}`}
            className={`size-16 shrink-0 overflow-hidden rounded-lg border-2 ${i === index ? "border-forest" : "border-transparent"}`}
            key={url}
            onClick={() => setIndex(i)}
            type="button"
          >
            <img alt="" className="size-full object-cover" src={url} />
          </button>
        ))}
      </div>
    </div>
  );
}

function Price({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-xl bg-forest-soft p-4">
      <p className="text-xs font-bold text-muted">{label}</p>
      <p className="mt-1 text-lg font-extrabold">
        {value ? money(value) : "Not offered"}
      </p>
    </div>
  );
}

function Reviews({ userId }: { userId: string }) {
  const reviews = useApi<Schemas["Review"][]>(
    `/reviews?user_id=${userId}&limit=3`,
  );
  if (!reviews.data?.length) return null;
  return (
    <ul className="mt-5 space-y-3 border-t border-line pt-5">
      {reviews.data.map((review) => (
        <li key={review.id} className="text-sm">
          <span className="font-bold">{"★".repeat(review.rating)}</span>{" "}
          <span className="text-muted">— {review.author_display_name}</span>
          {review.comment && <p className="mt-1 leading-6">{review.comment}</p>}
        </li>
      ))}
    </ul>
  );
}

function OwnerPanel({
  listing,
  onChange,
}: {
  listing: Schemas["ListingDetail"];
  onChange: (listing: Schemas["ListingDetail"]) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const next = listing.status === "active" ? "paused" : "active";

  async function toggle() {
    setBusy(true);
    setError(undefined);
    try {
      onChange(
        await apiRequest<Schemas["ListingDetail"]>(`/listings/${listing.id}`, {
          method: "PATCH",
          body: JSON.stringify({ status: next }),
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <strong className="text-lg">This is your listing</strong>
      <p className="mt-2 text-sm leading-6 text-muted">
        {listing.status === "active"
          ? "It is visible in search. Pause it while the item is unavailable."
          : "It is hidden from search. Reactivate it to take bookings again."}
      </p>
      {error && (
        <div className="mt-4">
          <Alert>{error}</Alert>
        </div>
      )}
      <div className="mt-5 flex flex-col gap-3">
        <Button
          busy={busy}
          onClick={toggle}
          variant={next === "paused" ? "secondary" : "primary"}
        >
          {next === "paused" ? "Pause listing" : "Reactivate listing"}
        </Button>
        <Link
          className="text-center text-sm font-bold underline"
          href={`/listings/${listing.id}/edit`}
        >
          Manage details, prices & open dates
        </Link>
      </div>
    </Card>
  );
}
