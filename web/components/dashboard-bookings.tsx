"use client";

import Link from "next/link";

import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

import { BookingRow } from "./booking-summary";
import { EmptyState, Spinner } from "./ui";

/** Bookings that need the viewer to do something, newest first. */
export function NeedsAction({ role }: { role: "borrower" | "lender" }) {
  const bookings = useApi<Schemas["Booking"][]>(`/bookings?role=${role}`);
  if (bookings.loading) return <Spinner />;
  const pending = bookings.data?.filter((b) => b.available_actions.some((a) => a !== "review")) ?? [];
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-extrabold">Needs your attention</h2>
        <Link className="text-sm font-bold underline" href={`/bookings?role=${role}`}>
          All bookings
        </Link>
      </div>
      {pending.length ? (
        pending.map((booking) => <BookingRow booking={booking} key={booking.id} />)
      ) : (
        <EmptyState title="You're all caught up" />
      )}
    </section>
  );
}
