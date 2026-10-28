"use client";
import { useAccountData } from "@/components/account-data";
import { ListingTile } from "@/components/listing-tile";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import {
  Alert,
  Button,
  EmptyState,
  LinkButton,
  PageHeader,
  Spinner,
} from "@/components/ui";

function SavedListings() {
  const { saved } = useAccountData();
  return (
    <>
      <PageHeader
        eyebrow="Profile"
        title="Saved listings"
        description="Keep useful items here for later."
      />
      {saved.loading && <Spinner label="Loading saved listings…" />}
      {saved.error && (
        <Alert>
          {saved.error.message}{" "}
          <Button onClick={saved.reload} variant="secondary">
            Try again
          </Button>
        </Alert>
      )}
      {saved.data?.length === 0 && (
        <EmptyState title="Nothing saved yet">
          <p>Use the bookmark on a listing to keep it here.</p>
          <LinkButton href="/search" className="mt-4">
            Browse rentals
          </LinkButton>
        </EmptyState>
      )}
      <div className="listing-grid">
        {saved.data?.map((listing) => (
          <ListingTile
            key={listing.id}
            listing={listing}
            href={`/listings/${listing.id}`}
          />
        ))}
      </div>
    </>
  );
}
export default function SavedListingsPage() {
  return (
    <PageShell>
      <RequireAuth>
        <SavedListings />
      </RequireAuth>
    </PageShell>
  );
}
