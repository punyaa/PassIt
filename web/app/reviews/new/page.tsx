"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useState } from "react";

import { BookingStep, WrongStep } from "@/components/booking-step-page";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import { Alert, Button, Card, Field, Textarea } from "@/components/ui";
import { apiPost, type Schemas } from "@/lib/api-client";

const LABELS = ["", "Poor", "Fair", "Good", "Great", "Excellent"];

function ReviewForm({ booking }: { booking: Schemas["Booking"] }) {
  const router = useRouter();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const other = booking.viewer_role === "borrower" ? "lender" : "borrower";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      await apiPost("/reviews", { booking_id: booking.id, rating, comment: comment.trim() || null });
      router.push(`/bookings/${booking.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn't post the review.");
      setBusy(false);
    }
  }

  return (
    <Card>
      <form className="space-y-6" onSubmit={submit}>
        <fieldset>
          <legend className="text-sm font-extrabold">How was the {other}?</legend>
          <div className="mt-3 flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                aria-label={`${value} star${value === 1 ? "" : "s"}`}
                aria-pressed={rating === value}
                className={`text-4xl transition ${value <= rating ? "text-orange" : "text-line"} hover:scale-110`}
                key={value}
                onClick={() => setRating(value)}
                type="button"
              >
                ★
              </button>
            ))}
            <span className="ml-2 text-sm font-bold text-muted">{LABELS[rating]}</span>
          </div>
        </fieldset>
        <Field label="Comment (optional)" hint="Shown on their profile.">
          <Textarea maxLength={1000} onChange={(e) => setComment(e.target.value)} value={comment} />
        </Field>
        {error && <Alert>{error}</Alert>}
        <Button busy={busy} disabled={!rating} type="submit" variant="accent">
          Post review
        </Button>
      </form>
    </Card>
  );
}

function ReviewContent() {
  const bookingId = useSearchParams().get("booking");
  if (!bookingId) return <Alert>Open this page from a completed booking.</Alert>;
  return (
    <BookingStep eyebrow="Review" id={bookingId} title="Leave a review">
      {(booking) =>
        booking.available_actions.includes("review") ? (
          <ReviewForm booking={booking} />
        ) : (
          <WrongStep booking={booking} message="Reviews open after the return, once per booking." />
        )
      }
    </BookingStep>
  );
}

export default function NewReviewPage() {
  return (
    <PageShell width="max-w-2xl">
      <RequireAuth>
        {() => (
          <Suspense>
            <ReviewContent />
          </Suspense>
        )}
      </RequireAuth>
    </PageShell>
  );
}
