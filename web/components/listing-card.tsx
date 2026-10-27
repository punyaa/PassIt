import Link from "next/link";

import type { Schemas } from "@/lib/api-client";
import { categoryIcon } from "@/lib/catalogue";
import { money } from "@/lib/format";

import { Badge } from "./ui";

export function ListingPhoto({ listing, className = "aspect-square" }: { listing: Schemas["Listing"]; className?: string }) {
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
      className="group overflow-hidden rounded-card border border-line bg-white transition hover:-translate-y-0.5 hover:shadow-md"
      href={href ?? `/listings/${listing.id}`}
    >
      <ListingPhoto listing={listing} />
      <div className="p-3 sm:p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-2 min-h-10 text-sm font-bold leading-5 sm:text-base">{listing.title}</h3>
          {listing.status !== "active" && <Badge tone="warning">{listing.status}</Badge>}
        </div>
        <p className="text-sm text-muted">{listing.mrt_station ? `${listing.mrt_station} MRT` : "Singapore"}</p>
        <div className="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <span className="text-base font-extrabold sm:text-lg">
            {money(listing.price_day)} <small className="text-xs font-normal text-muted">/ day</small>
          </span>
          <span className="text-xs text-muted">{listing.condition}</span>
        </div>
      </div>
    </Link>
  );
}
