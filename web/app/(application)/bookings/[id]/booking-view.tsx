"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ConfirmAction } from "@/components/confirm-action";
import { useAccountData } from "@/components/account-data";
import { BookingStateBadge } from "@/components/booking-state";
import { LedgerTable, settlement } from "@/components/booking-summary";
import { Alert, Card, LinkButton, Spinner } from "@/components/ui";
import { apiPost, type Schemas } from "@/lib/api-client";
import {
  dateRange,
  formatDate,
  formatDateTime,
  money,
  timeUntil,
} from "@/lib/format";
import { useApi } from "@/lib/use-api";

type Booking = Schemas["Booking"];

const STEPS: { state: Booking["state"]; label: string }[] = [
  { state: "confirmed", label: "Booked" },
  { state: "handed_over", label: "Handed over" },
  { state: "returned", label: "Returned" },
  { state: "settled", label: "Completed" },
];

export function BookingView({ id }: { id: string }) {
  const { rentals } = useAccountData();
  const booking = useApi<Booking>(`/bookings/${id}`);
  const ledger = useApi<Schemas["LedgerEntry"][]>(`/bookings/${id}/ledger`);
  const isNew = useSearchParams().get("new") === "1";
  const releaseAt = booking.data?.fee_released
    ? null
    : booking.data?.fee_release_at;
  const { reload: reloadBooking } = booking;
  const { reload: reloadLedger } = ledger;

  // Once the hold period is over, poll until the scheduled release lands.
  useEffect(() => {
    if (!releaseAt) return;
    const timer = setInterval(() => {
      if (Date.now() >= new Date(releaseAt).getTime()) {
        reloadBooking();
        reloadLedger();
      }
    }, 10_000);
    return () => clearInterval(timer);
  }, [releaseAt, reloadBooking, reloadLedger]);

  if (booking.loading && !booking.data)
    return <Spinner label="Loading booking…" />;
  if (booking.error || !booking.data)
    return <Alert>{booking.error?.message ?? "Booking not found."}</Alert>;
  const b = booking.data;
  const refresh = (updated: Booking) => {
    booking.setData(updated);
    ledger.reload();
    rentals.reload();
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <div className="space-y-6">
        {isNew && b.state === "confirmed" && (
          <Alert tone="success" title="You're booked!">
            The fee and deposit are on hold. Meet on {formatDate(b.start_date)}{" "}
            and record the handover together.
          </Alert>
        )}
        <div>
          <Link
            className="text-sm font-bold text-muted"
            href={`/bookings?role=${b.viewer_role}`}
          >
            ← All bookings
          </Link>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="text-4xl font-extrabold tracking-[-0.045em]">
              {b.listing_title}
            </h1>
            <BookingStateBadge state={b.state} />
          </div>
          <p className="mt-2 text-muted">
            {dateRange(b.start_date, b.end_date)} ·{" "}
            {b.viewer_role === "borrower" ? "You're renting" : "You're lending"}{" "}
            ·{" "}
            <Link className="underline" href={`/listings/${b.listing_id}`}>
              View listing
            </Link>
          </p>
        </div>

        {b.state !== "cancelled" && <Progress state={b.state} />}
        <NextStep booking={b} entries={ledger.data ?? []} onChange={refresh} />
      </div>

      <aside className="space-y-6">
        <Card>
          <h2 className="font-extrabold">Price</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">Rental fee (per {b.duration_type})</dt>
              <dd className="font-bold">{money(b.fee)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Deposit</dt>
              <dd className="font-bold">{money(b.deposit)}</dd>
            </div>
          </dl>
        </Card>
        <Card>
          <h2 className="font-extrabold">Your money</h2>
          <p className="mb-3 text-xs text-muted">
            Simulated ledger — no real payments move.
          </p>
          {ledger.data ? (
            <LedgerTable entries={ledger.data} role={b.viewer_role} />
          ) : (
            <Spinner />
          )}
        </Card>
        {b.state !== "confirmed" && b.state !== "cancelled" && (
          <Link
            className="block text-center text-sm font-bold underline"
            href={`/returns/${b.id}?view=evidence`}
          >
            View condition evidence
          </Link>
        )}
      </aside>
    </div>
  );
}

function Progress({ state }: { state: Booking["state"] }) {
  const current = STEPS.findIndex((step) => step.state === state);
  return (
    <ol className="grid grid-cols-4 gap-2">
      {STEPS.map((step, index) => (
        <li key={step.state}>
          <div
            className={`h-2 rounded-full ${index <= current ? "bg-forest" : "bg-line"}`}
          />
          <span
            className={`mt-2 block text-xs font-bold ${index <= current ? "text-ink" : "text-muted"}`}
          >
            {step.label}
          </span>
        </li>
      ))}
    </ol>
  );
}

function useNow(intervalMs = 30_000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}

function FeeRelease({ booking }: { booking: Booking }) {
  const now = useNow();
  if (booking.fee_released) {
    return (
      <p className="text-sm font-bold text-success">
        ✓ Rental fee released to the lender
      </p>
    );
  }
  if (!booking.fee_release_at) return null;
  return (
    <p className="text-sm text-muted">
      Fee releases to the lender in{" "}
      <strong className="text-ink">
        {timeUntil(booking.fee_release_at, now)}
      </strong>{" "}
      ({formatDateTime(booking.fee_release_at)}).
    </p>
  );
}

function NextStep({
  booking: b,
  entries,
  onChange,
}: {
  booking: Booking;
  entries: Schemas["LedgerEntry"][];
  onChange: (booking: Booking) => void;
}) {
  const can = (action: Booking["available_actions"][number]) =>
    b.available_actions.includes(action);
  const lender = b.viewer_role === "lender";

  const outcome = settlement(entries);

  return (
    <Card className="space-y-4">
      {b.state === "confirmed" && (
        <>
          <h2 className="text-xl font-extrabold">Next: hand over the item</h2>
          <p className="text-sm leading-6 text-muted">
            When you meet, photograph the item and tick the checklist together.
            These photos protect both of you if anything is damaged.
          </p>
          <div className="flex flex-wrap gap-3">
            {can("handover") && (
              <LinkButton href={`/handover/${b.id}`}>Start handover</LinkButton>
            )}
            {can("cancel") && (
              <ConfirmAction
                title="Cancel this booking?"
                description={`The ${money(b.fee)} rental fee and ${money(b.deposit)} deposit will be refunded in full.`}
                trigger="Cancel booking"
                confirmLabel="Confirm cancellation"
                variant="secondary"
                disabled={false}
                onConfirm={async () => {
                  onChange(await apiPost<Booking>(`/bookings/${b.id}/cancel`));
                }}
              />
            )}
          </div>
        </>
      )}
      {b.state === "handed_over" && (
        <>
          <h2 className="text-xl font-extrabold">
            {lender ? "Item is with the borrower" : "Enjoy the rental"}
          </h2>
          <p className="text-sm text-muted">
            Handed over {formatDateTime(b.handed_over_at)}. Due back by the end
            of the booking.
          </p>
          <FeeRelease booking={b} />
          {can("return") && (
            <LinkButton href={`/returns/${b.id}`}>Record the return</LinkButton>
          )}
        </>
      )}
      {b.state === "returned" && (
        <>
          <h2 className="text-xl font-extrabold">
            {lender
              ? "Check the item and settle the deposit"
              : "Waiting for the lender"}
          </h2>
          <p className="text-sm leading-6 text-muted">
            {lender
              ? "Compare the return photos with the handover photos. If all is well, refund the deposit. If not, report damage."
              : `The lender is checking the item. Your ${money(b.deposit)} deposit is refunded once they confirm.`}
          </p>
          <FeeRelease booking={b} />
          <div className="flex flex-wrap gap-3">
            {can("settle") && (
              <ConfirmAction
                title="Confirm the item is fine?"
                description={`Refund the full ${money(b.deposit)} deposit to the borrower. You cannot report damage after settling the deposit.`}
                trigger="Item is fine — refund deposit"
                confirmLabel={`Refund ${money(b.deposit)} deposit`}
                variant="primary"
                disabled={false}
                onConfirm={async () => {
                  onChange(await apiPost<Booking>(`/bookings/${b.id}/settle`));
                }}
              />
            )}
            {can("report_damage") && (
              <LinkButton href={`/damage/${b.id}`} variant="secondary">
                Report damage
              </LinkButton>
            )}
          </div>
        </>
      )}
      {b.state === "settled" && (
        <>
          <h2 className="text-xl font-extrabold">Rental complete</h2>
          {b.damage_severity && b.damage_severity !== "none" ? (
            <p className="text-sm leading-6">
              Damage assessed as <strong>{b.damage_severity}</strong>:{" "}
              {money(outcome.damagePaid)} of the deposit went to the lender and{" "}
              {money(outcome.depositRefunded)} was refunded.{" "}
              <Link className="font-bold underline" href={`/damage/${b.id}`}>
                See details
              </Link>
            </p>
          ) : (
            <p className="text-sm text-muted">
              The {money(b.deposit)} deposit was refunded in full.
            </p>
          )}
          <FeeRelease booking={b} />
        </>
      )}
      {b.state === "cancelled" && (
        <>
          <h2 className="text-xl font-extrabold">Booking cancelled</h2>
          <p className="text-sm text-muted">
            Cancelled {formatDateTime(b.cancelled_at)}. All holds were refunded.
          </p>
        </>
      )}
      {b.state === "disputed" && (
        <>
          <h2 className="text-xl font-extrabold">Under review</h2>
          <p className="text-sm text-muted">
            PassIt is reviewing this rental. Payouts are paused until it is
            resolved.
          </p>
        </>
      )}
      {can("review") && (
        <div className="border-t border-line pt-4">
          <LinkButton href={`/reviews/new?booking=${b.id}`} variant="accent">
            Review the {lender ? "borrower" : "lender"}
          </LinkButton>
        </div>
      )}
    </Card>
  );
}
