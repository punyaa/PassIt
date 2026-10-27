"use client";

import { ListingCard } from "./listing-card";
import { Alert, Button, EmptyState, Spinner } from "./ui";
import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

export function CatalogueGrid({ path, manage }: { path: string; manage: boolean }) {
  const listings = useApi<Schemas["Listing"][]>(path);
  return <>
    {listings.loading && <Spinner label="Loading listings…" />}
    {listings.error && <Alert>{listings.error.message} <Button onClick={listings.reload} variant="secondary">Try again</Button></Alert>}
    {!listings.loading && listings.data?.length === 0 && <EmptyState title={manage ? "Your next listing starts here" : "No rentals yet"}>{manage ? "List something you can lend to your neighbours." : "Check back soon for more items."}</EmptyState>}
    <div className="listing-grid">{listings.data?.map((listing) => <ListingCard key={listing.id} listing={listing} href={manage ? `/listings/${listing.id}/edit` : `/listings/${listing.id}`} />)}</div>
  </>;
}
