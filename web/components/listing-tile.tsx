"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { Schemas } from "@/lib/api-client";
import { useAccountData } from "./account-data";
import { ListingCard, ListingPhoto } from "./listing-card";
import { useSession } from "./session";

export function SaveListingButton({ id }: { id: string }) {
  const { user } = useSession();
  const { saved, toggleSaved } = useAccountData();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pathname = usePathname();
  const router = useRouter();
  const isSaved = saved.data?.some((listing) => listing.id === id) ?? false;
  async function toggle() {
    if (!user) {
      router.push(
        `/login?next=${encodeURIComponent(pathname + window.location.search)}`,
      );
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await toggleSaved(id, isSaved);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Couldn't save this item.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <button
        type="button"
        aria-label={isSaved ? "Unsave listing" : "Save listing"}
        aria-pressed={isSaved}
        disabled={busy || (user !== null && saved.loading)}
        onClick={toggle}
        className="grid size-10 place-items-center rounded-full border border-line bg-white text-forest shadow-sm disabled:opacity-50"
      >
        <svg
          aria-hidden="true"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill={isSaved ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth="1.8"
        >
          <path d="M6 3h12v18l-6-4-6 4z" />
        </svg>
      </button>
      {(error || saved.error) && (
        <p
          role="alert"
          className="mt-2 max-w-48 rounded-lg bg-white p-2 text-xs text-danger"
        >
          {error ?? "Saved items couldn't load."}
          <button
            type="button"
            className="ml-1 underline"
            onClick={() => {
              setError(null);
              saved.reload();
            }}
          >
            Retry
          </button>
        </p>
      )}
    </div>
  );
}

export function ListingTile({
  listing,
  href,
}: {
  listing: Schemas["Listing"];
  href: string;
}) {
  return (
    <div className="relative min-w-0 [&>a]:block [&>a]:h-full">
      {listing.status === "archived" ? (
        <div className="h-full overflow-hidden rounded-card border border-line bg-white">
          <ListingPhoto listing={listing} />
          <div className="p-4">
            <h3 className="font-bold">{listing.title}</h3>
            <p className="mt-2 text-sm text-muted">No longer available</p>
          </div>
        </div>
      ) : (
        <ListingCard listing={listing} href={href} />
      )}
      <div className="absolute right-2 top-2">
        <SaveListingButton id={listing.id} />
      </div>
    </div>
  );
}
