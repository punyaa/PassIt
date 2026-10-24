"use client";

import { useRouter, useSearchParams } from "next/navigation";

import { BookingRow } from "@/components/booking-summary";
import { Alert, EmptyState, LinkButton, PageHeader, Spinner } from "@/components/ui";
import { type Schemas, withQuery } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

const TABS = [
  { role: "borrower", label: "Renting" },
  { role: "lender", label: "Lending" },
] as const;

const ACTIVE = new Set(["confirmed", "handed_over", "returned", "disputed"]);

export function BookingList() {
  const params = useSearchParams();
  const router = useRouter();
  const role = params.get("role") === "lender" ? "lender" : "borrower";
  const bookings = useApi<Schemas["Booking"][]>(withQuery("/bookings", { role }));
  const current = bookings.data?.filter((b) => ACTIVE.has(b.state)) ?? [];
  const past = bookings.data?.filter((b) => !ACTIVE.has(b.state)) ?? [];

  return (
    <>
      <PageHeader eyebrow="Bookings" title="Your rentals" />
      <div className="mb-6 inline-flex rounded-xl border border-line bg-white p-1" role="tablist">
        {TABS.map((tab) => (
          <button
            aria-selected={role === tab.role}
            className="rounded-lg px-5 py-2 text-sm font-extrabold aria-selected:bg-forest aria-selected:text-white"
            key={tab.role}
            onClick={() => router.replace(`/bookings?role=${tab.role}`)}
            role="tab"
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {bookings.loading && <Spinner label="Loading bookings…" />}
      {bookings.error && <Alert>{bookings.error.message}</Alert>}
      {bookings.data?.length === 0 && (
        <EmptyState title={role === "borrower" ? "You haven't rented anything yet" : "No one has booked your items yet"}>
          <div className="mt-4">
            {role === "borrower" ? (
              <LinkButton href="/search">Explore rentals</LinkButton>
            ) : (
              <LinkButton href="/listings/new">List an item</LinkButton>
            )}
          </div>
        </EmptyState>
      )}
      {current.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-extrabold">Current</h2>
          {current.map((booking) => (
            <BookingRow booking={booking} key={booking.id} />
          ))}
        </section>
      )}
      {past.length > 0 && (
        <section className="mt-10 space-y-3">
          <h2 className="text-lg font-extrabold">Past</h2>
          {past.map((booking) => (
            <BookingRow booking={booking} key={booking.id} />
          ))}
        </section>
      )}
    </>
  );
}
