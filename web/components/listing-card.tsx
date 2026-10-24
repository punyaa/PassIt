import Link from "next/link";

import type { Schemas } from "@/lib/api-client";
import { categoryIcon } from "@/lib/catalogue";
import { money } from "@/lib/format";

import { Badge } from "./ui";

export function ListingPhoto({ listing, className = "h-44" }: { listing: Schemas["Listing"]; className?: string }) {
  const photo = listing.photo_urls?.[0];
  return photo ? (
    <img alt={listing.title} className={`w-full object-cover ${className}`} src={photo} />
  ) : (
    <div className={`grid place-items-center bg-gradient-to-br from-[#aacbb8] to-[#d9e7bc] text-7xl ${className}`}>
      {categoryIcon(listing.category)}
    </div>
  );
}

export function ListingCard({ listing, href }: { listing: Schemas["Listing"]; href?: string }) {
  return (
    <Link
      className="group overflow-hidden rounded-card border border-line bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
      href={href ?? `/listings/${listing.id}`}
    >
      <ListingPhoto listing={listing} />
      <div className="p-5">
        <div className="flex items-start justify-between gap-2">
          <h3 className="min-h-12 text-lg font-extrabold leading-6">{listing.title}</h3>
          {listing.status !== "active" && <Badge tone="warning">{listing.status}</Badge>}
        </div>
        <p className="text-sm text-muted">📍 {listing.mrt_station ?? "Singapore"} MRT</p>
        <div className="mt-4 flex items-baseline justify-between border-t border-line pt-3">
          <span className="text-xl font-extrabold">
            {money(listing.price_day)} <small className="text-xs font-normal text-muted">/ day</small>
          </span>
          <span className="text-xs text-muted">{listing.condition}</span>
        </div>
      </div>
    </Link>
  );
}
