"use client";

import Link from "next/link";

import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

import { BookingRow } from "./booking-summary";
import { Alert, Button, EmptyState, Spinner } from "./ui";

/** Bookings that need the viewer to do something, newest first. */
export function NeedsAction({
  role,
  compact,
}: {
  role: "borrower" | "lender";
  compact: boolean;
}) {
  const bookings = useApi<Schemas["Booking"][]>(`/bookings?role=${role}`);
  if (bookings.loading) return <Spinner />;
  if (bookings.error)
    return (
      <Alert>
        {bookings.error.message}
        <Button onClick={bookings.reload} variant="secondary">
          Try again
        </Button>
      </Alert>
    );
  const pending =
    bookings.data?.filter((b) =>
      b.available_actions.some((a) => a !== "review" && a !== "cancel"),
    ) ?? [];
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-extrabold">
          {compact
            ? role === "borrower"
              ? "Renting"
              : "Lending"
            : "Needs your attention"}
        </h2>
        <Link
          className="text-sm font-bold underline"
          href={`/bookings?role=${role}`}
        >
          All bookings
        </Link>
      </div>
      {pending.length ? (
        (compact ? pending.slice(0, 2) : pending).map((booking) => (
          <BookingRow booking={booking} key={booking.id} />
        ))
      ) : compact ? (
        <p className="text-sm text-muted">You're all caught up.</p>
      ) : (
        <EmptyState title="You're all caught up" />
      )}
    </section>
  );
}
