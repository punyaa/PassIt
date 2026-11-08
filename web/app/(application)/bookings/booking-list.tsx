"use client";

import { useRouter, useSearchParams } from "next/navigation";

import { BookingRow } from "@/components/booking-summary";
import {
  Alert,
  EmptyState,
  LinkButton,
  PageHeader,
  Spinner,
} from "@/components/ui";
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
  const bookings = useApi<Schemas["Booking"][]>(
    withQuery("/bookings", { role }),
  );
  const history = params.get("view") === "history";
  const current = bookings.data?.filter((b) => ACTIVE.has(b.state)) ?? [];
  const past = bookings.data?.filter((b) => !ACTIVE.has(b.state)) ?? [];

  const pastCount = past.length;

  return (
    <>
      <PageHeader
        eyebrow="Rentals"
        title="Your rentals"
        description="Pickups, returns and everything in between."
      />
      <div
        className="mb-6 inline-flex rounded-xl border border-line bg-white p-1"
        aria-label="Rental role"
      >
        {TABS.map((tab) => (
          <button
            aria-pressed={role === tab.role}
            className="rounded-lg px-5 py-2 text-sm font-extrabold aria-pressed:bg-forest aria-pressed:text-white"
            key={tab.role}
            onClick={() =>
              router.replace(
                withQuery("/bookings", {
                  role: tab.role,
                  view: history ? "history" : null,
                }),
              )
            }
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {bookings.loading && <Spinner label="Loading bookings…" />}
      {bookings.error && <Alert>{bookings.error.message}</Alert>}
      <div className="mb-6 flex gap-2" aria-label="Rental period">
        {([false, true] as const).map((past) => (
          <button
            key={String(past)}
            type="button"
            aria-pressed={history === past}
            className="rounded-full border border-line px-4 py-2 text-sm font-bold aria-pressed:border-forest aria-pressed:bg-sage"
            onClick={() =>
              router.replace(
                withQuery("/bookings", { role, view: past ? "history" : null }),
              )
            }
          >
            {past ? "History" : "Active"} ({past ? pastCount : current.length})
          </button>
        ))}
      </div>
      {!bookings.loading &&
        bookings.data &&
        (history ? past : current).length === 0 && (
          <EmptyState
            title={history ? "No rental history yet" : "No active rentals"}
          >
            <p>
              {role === "borrower"
                ? "Find something for your next project or adventure."
                : "Your upcoming lending bookings will appear here."}
            </p>
            <div className="mt-4">
              <LinkButton
                href={role === "borrower" ? "/search" : "/listings/manage"}
              >
                {role === "borrower" ? "Explore rentals" : "Manage listings"}
              </LinkButton>
            </div>
          </EmptyState>
        )}
      <section
        className="space-y-3"
        aria-label={history ? "Rental history" : "Active rentals"}
      >
        {(history ? past : current).map((booking) => (
          <BookingRow booking={booking} key={booking.id} />
        ))}
      </section>
    </>
  );
}
