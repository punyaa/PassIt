"use client";

import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

import { ListingCard } from "./listing-card";
import { EmptyState, LinkButton } from "./ui";

export function FeaturedListings() {
  const listings = useApi<Schemas["Listing"][]>("/listings?limit=8");
  if (listings.loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div className="h-80 animate-pulse rounded-card bg-white" key={i} />
        ))}
      </div>
    );
  }
  if (!listings.data?.length) {
    return (
      <EmptyState title={listings.error ? "Listings are unavailable right now" : "Be the first to list something"}>
        <div className="mt-4">
          <LinkButton href="/listings/new">List an item</LinkButton>
        </div>
      </EmptyState>
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {listings.data.map((listing) => (
        <ListingCard key={listing.id} listing={listing} />
      ))}
    </div>
  );
}
