"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import type { Schemas } from "@/lib/api-client";
import { dateRange } from "@/lib/format";
import { useApi } from "@/lib/use-api";

import { BookingStateBadge } from "./booking-state";
import { Alert, PageHeader, Spinner } from "./ui";

/** Loads a booking and renders a step screen for it, with consistent header and errors. */
export function BookingStep({
  id,
  eyebrow,
  title,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  children: (booking: Schemas["Booking"], reload: () => void) => ReactNode;
}) {
  const booking = useApi<Schemas["Booking"]>(`/bookings/${id}`);
  if (booking.loading) return <Spinner label="Loading booking…" />;
  if (booking.error || !booking.data)
    return <Alert>{booking.error?.message ?? "Booking not found."}</Alert>;
  const b = booking.data;
  return (
    <>
      <Link className="text-sm font-bold text-muted" href={`/bookings/${b.id}`}>
        ← Back to booking
      </Link>
      <div className="mt-3">
        <PageHeader
          eyebrow={eyebrow}
          title={title}
          description={
            <span className="flex flex-wrap items-center gap-2">
              {b.listing_title} · {dateRange(b.start_date, b.end_date)}{" "}
              <BookingStateBadge state={b.state} />
            </span>
          }
        />
      </div>
      {children(b, booking.reload)}
    </>
  );
}

export function WrongStep({
  booking,
  message,
}: {
  booking: Schemas["Booking"];
  message: string;
}) {
  return (
    <Alert tone="info" title={message}>
      <Link className="font-bold underline" href={`/bookings/${booking.id}`}>
        Go to the booking
      </Link>{" "}
      to see what happens next.
    </Alert>
  );
}
