"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { CheckoutDialog, type PaymentDetails } from "@/components/checkout-dialog";
import { useSession } from "@/components/session";
import { Alert, Button, Card, Field, Input, Select } from "@/components/ui";
import {
  ApiError,
  apiPost,
  apiRequest,
  type Schemas,
  withQuery,
} from "@/lib/api-client";
import { isPlusPlan, PLUS_PLAN_NAMES } from "@/lib/auth";
import { DEPOSIT_FACTOR } from "@/lib/plus-plans";
import {
  addDays,
  dateRange,
  inclusiveDays,
  isoDate,
  money,
} from "@/lib/format";

type Duration = Schemas["BookingCreate"]["duration_type"];
const UNIT_DAYS: Record<Duration, number> = { day: 1, week: 7, month: 30 };

/** Mirrors the API's pricing: whole units of the chosen duration, rounded up. */
function estimate(
  listing: Schemas["ListingDetail"],
  duration: Duration,
  days: number,
) {
  const rate = {
    day: listing.price_day,
    week: listing.price_week,
    month: listing.price_month,
  }[duration];
  if (!rate) return null;
  const units = Math.ceil(days / UNIT_DAYS[duration]);
  return { units, fee: Number(rate) * units };
}

export function BookingPanel({
  listing,
}: {
  listing: Schemas["ListingDetail"];
}) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useSession();
  const today = isoDate(new Date());
  const [start, setStart] = useState(params.get("from") || addDays(today, 1));
  const [end, setEnd] = useState(params.get("to") || addDays(today, 2));
  const durations = (["day", "week", "month"] as Duration[]).filter(
    (d) =>
      ({
        day: listing.price_day,
        week: listing.price_week,
        month: listing.price_month,
      })[d],
  );
  const [duration, setDuration] = useState<Duration>("day");
  const [availability, setAvailability] =
    useState<Schemas["AvailabilityResponse"]>();
  const [checking, setChecking] = useState(true);
  const [availabilityError, setAvailabilityError] = useState(false);
  const [error, setError] = useState<string>();
  const [version, setVersion] = useState(0);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [notice, setNotice] = useState<{ tone: "success" | "info"; text: string }>();
  // Plus members pay a share of the deposit; the API applies the same factor.
  const userPlan = user?.plan ?? null;
  const plan = isPlusPlan(userPlan) ? userPlan : "saver";
  const deposit = Math.round(Number(listing.deposit) * DEPOSIT_FACTOR[plan] * 100) / 100;
  const depositNote = plan === "saver" ? undefined : `${PLUS_PLAN_NAMES[plan]} price`;

  const validRange = start >= today && end >= start;
  const days = validRange ? inclusiveDays(start, end) : 0;
  const quote = useMemo(
    () => (days ? estimate(listing, duration, days) : null),
    [listing, duration, days],
  );

  useEffect(() => {
    if (!validRange) return;
    let active = true;
    setChecking(true);
    setAvailabilityError(false);
    const timer = setTimeout(() => {
      apiRequest<Schemas["AvailabilityResponse"]>(
        withQuery(`/listings/${listing.id}/availability`, {
          from: start,
          to: end,
        }),
      )
        .then((result) => active && setAvailability(result))
        .catch(() => {
          if (active) {
            setAvailability(undefined);
            setAvailabilityError(true);
          }
        })
        .finally(() => active && setChecking(false));
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [listing.id, start, end, validRange, version]);

  async function markPaid(details: PaymentDetails): Promise<void> {
    setError(undefined);
    try {
      const booking = await apiPost<Schemas["Booking"]>("/bookings", {
        listing_id: listing.id,
        start_date: start,
        end_date: end,
        duration_type: duration,
        payment_method_token: "pm_mock_success",
      });
      setCheckoutOpen(false);
      const card = details.method === "credit/debit card" && /^\d{4}$/.test(details.reference);
      const via = details.method
        ? ` by ${details.method}${card ? ` ending ${details.reference}` : ""}`
        : "";
      const by = details.name.trim() ? ` (${details.name.trim()})` : "";
      setNotice({
        tone: "success",
        text: `Successfully paid${via}${by}. Taking you to your booking for handover…`,
      });
      setTimeout(() => router.push(`/bookings/${booking.id}?new=1`), 1500);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setCheckoutOpen(false);
        setError(
          caught.message.includes("availability")
            ? "The lender isn't offering those dates. Pick dates inside their open windows."
            : "Someone just booked those dates. Please choose different dates.",
        );
        setVersion((value) => value + 1);
        return;
      }
      throw caught; // shown inside the payment portal
    }
  }

  function cancelPayment() {
    setCheckoutOpen(false);
    setNotice({ tone: "info", text: "Payment cancelled. Nothing was booked or charged." });
  }

  const currentAvailability =
    availability?.from_date === start && availability?.to_date === end
      ? availability
      : undefined;
  const unavailable = currentAvailability && !currentAvailability.available;
  const canBook =
    validRange &&
    listing.status === "active" &&
    quote &&
    currentAvailability?.available &&
    !checking;

  return (
    <Card className="shadow-lg">
      <p className="text-2xl font-extrabold">
        {money(listing.price_day)}{" "}
        <small className="text-sm font-normal text-muted">/ day</small>
      </p>
      <div className="mt-5 grid grid-cols-2 gap-3">
        <Field label="Pick up">
          <Input
            min={today}
            onChange={(e) => {
              setStart(e.target.value);
              if (e.target.value > end) setEnd(e.target.value);
            }}
            type="date"
            value={start}
          />
        </Field>
        <Field label="Return">
          <Input
            min={start || today}
            onChange={(e) => setEnd(e.target.value)}
            type="date"
            value={end}
          />
        </Field>
      </div>
      {durations.length > 1 && (
        <div className="mt-3">
          <Field label="Charge by">
            <Select
              onChange={(e) => setDuration(e.target.value as Duration)}
              value={duration}
            >
              {durations.map((d) => (
                <option key={d} value={d}>
                  {d === "day" ? "Day" : d === "week" ? "Week" : "Month"}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      )}

      <div className="mt-4 min-h-6 text-sm" aria-live="polite">
        {!validRange && (
          <span className="font-bold text-danger">
            Choose a return date on or after pick-up, from today.
          </span>
        )}
        {validRange && checking && (
          <span className="text-muted">Checking availability…</span>
        )}
        {validRange && !checking && currentAvailability?.available && (
          <span className="font-bold text-success">✓ Available</span>
        )}
        {validRange && !checking && unavailable && (
          <span className="font-bold text-danger">
            {currentAvailability.booked.length
              ? `Booked ${currentAvailability.booked.map((b) => dateRange(b.start_date, b.end_date)).join(", ")}`
              : "Outside the lender's available dates"}
          </span>
        )}
        {validRange && !checking && availabilityError && (
          <Alert>
            Couldn't check these dates.{" "}
            <button
              type="button"
              className="font-bold underline"
              onClick={() => setVersion((value) => value + 1)}
            >
              Try again
            </button>
          </Alert>
        )}
      </div>

      {quote && validRange && (
        <dl className="mt-4 space-y-2 border-t border-line pt-4 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted">
              {quote.units} {duration}
              {quote.units === 1 ? "" : "s"}
              {duration !== "day" && ` · ${days} day${days === 1 ? "" : "s"}`}
            </dt>
            <dd className="font-bold">{money(quote.fee)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Refundable deposit</dt>
            <dd className="font-bold">{money(deposit)}</dd>
          </div>
          <div className="flex justify-between border-t border-line pt-2 text-base">
            <dt className="font-extrabold">Held today</dt>
            <dd className="font-extrabold">
              {money(quote.fee + deposit)}
            </dd>
          </div>
        </dl>
      )}

      {error && (
        <div className="mt-4">
          <Alert>{error}</Alert>
        </div>
      )}
      {notice && (
        <div className="mt-4">
          <Alert tone={notice.tone}>{notice.text}</Alert>
        </div>
      )}

      <div className="mt-5">
        {user ? (
          <Button
            className="w-full"
            disabled={!canBook || notice?.tone === "success"}
            onClick={() => {
              setError(undefined);
              setNotice(undefined);
              setCheckoutOpen(true);
            }}
            variant="accent"
          >
            Book now
          </Button>
        ) : (
          <Link
            className="block rounded-xl bg-orange px-5 py-3 text-center text-sm font-extrabold"
            href={`/login?next=${encodeURIComponent(withQuery(pathname, { from: start, to: end, back: params.get("back") }))}`}
          >
            Log in to book
          </Link>
        )}
      </div>
      {quote && (
        <CheckoutDialog
          open={checkoutOpen}
          onCancel={cancelPayment}
          onMarkPaid={markPaid}
          title={listing.title}
          dates={dateRange(start, end)}
          fee={quote.fee}
          deposit={deposit}
          depositNote={depositNote}
        />
      )}
      <p className="mt-3 text-xs leading-5 text-muted">
        Payments are simulated. PassIt holds the fee and releases it to the
        lender after a short hold period that starts at handover; the deposit
        comes back once the item is returned.
      </p>
    </Card>
  );
}
