"use client";

import Link from "next/link";
import { type FormEvent, use, useState } from "react";

import { BookingStep, WrongStep } from "@/components/booking-step-page";
import { settlement } from "@/components/booking-summary";
import { EvidenceCompare } from "@/components/evidence";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import { Alert, Button, Card, Field, LinkButton, Spinner, Stat, Textarea } from "@/components/ui";
import { apiPost, type Schemas } from "@/lib/api-client";
import { money } from "@/lib/format";
import { useApi } from "@/lib/use-api";

type Severity = Schemas["DamageSubmission"]["severity"];

/** Must match DAMAGE_TIERS in api/app/transactions/ledger.py. */
const TIERS: { severity: Severity; share: number; label: string; example: string }[] = [
  { severity: "minor", share: 0.2, label: "Minor", example: "Scuffs or scratches; works normally." },
  { severity: "moderate", share: 0.4, label: "Moderate", example: "Visible damage or a missing small part." },
  { severity: "severe", share: 0.7, label: "Severe", example: "Partly broken; needs repair to be usable." },
  { severity: "total", share: 1, label: "Total loss", example: "Destroyed, lost or beyond repair." },
];

function split(deposit: string, share: number) {
  const payout = Math.round(Number(deposit) * share * 100) / 100;
  return { payout, refund: Number(deposit) - payout };
}

function Outcome({ booking }: { booking: Schemas["Booking"] }) {
  const ledger = useApi<Schemas["LedgerEntry"][]>(`/bookings/${booking.id}/ledger`);
  if (!ledger.data) return <Spinner />;
  const result = settlement(ledger.data);
  const damaged = booking.damage_severity && booking.damage_severity !== "none";
  return (
    <div className="space-y-6">
      <Alert tone={damaged ? "info" : "success"} title={damaged ? `Damage assessed: ${booking.damage_severity}` : "No damage reported"}>
        The {money(booking.deposit)} deposit has been settled.
      </Alert>
      <div className="grid gap-4 sm:grid-cols-2">
        <Stat label="Paid to lender for damage" value={money(result.damagePaid)} />
        <Stat label="Refunded to borrower" value={money(result.depositRefunded)} />
      </div>
      <LinkButton href={`/bookings/${booking.id}`} variant="secondary">
        Back to booking
      </LinkButton>
    </div>
  );
}

function DamageForm({ booking }: { booking: Schemas["Booking"] }) {
  const checklists = useApi<Schemas["ChecklistRecord"][]>(`/bookings/${booking.id}/checklists`);
  const [severity, setSeverity] = useState<Severity>();
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [result, setResult] = useState<Schemas["Booking"]>();

  if (result) return <Outcome booking={result} />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!severity) return setError("Choose how serious the damage is.");
    const { payout } = split(booking.deposit, TIERS.find((t) => t.severity === severity)!.share);
    if (!window.confirm(`Claim ${money(payout)} of the deposit for ${severity} damage? This can't be undone.`)) return;
    setBusy(true);
    setError(undefined);
    try {
      setResult(await apiPost<Schemas["Booking"]>(`/bookings/${booking.id}/damage`, { severity, notes: notes.trim() }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn't submit the report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-8" onSubmit={submit}>
      <section>
        <h2 className="mb-3 text-lg font-extrabold">Compare the evidence</h2>
        {checklists.data ? <EvidenceCompare checklists={checklists.data} /> : <Spinner />}
      </section>
      <Card className="space-y-4">
        <h2 className="text-xl font-extrabold">How serious is the damage?</h2>
        <p className="text-sm text-muted">
          Each level pays a fixed share of the {money(booking.deposit)} deposit to you; the rest goes back to the borrower.
        </p>
        <div className="grid gap-3 sm:grid-cols-2" role="radiogroup">
          {TIERS.map((tier) => {
            const { payout, refund } = split(booking.deposit, tier.share);
            return (
              <label
                className="cursor-pointer rounded-xl border-2 border-line p-4 has-checked:border-forest has-checked:bg-forest-soft"
                key={tier.severity}
              >
                <input
                  checked={severity === tier.severity}
                  className="sr-only"
                  name="severity"
                  onChange={() => setSeverity(tier.severity)}
                  type="radio"
                />
                <span className="flex justify-between font-extrabold">
                  {tier.label} <span>{Math.round(tier.share * 100)}%</span>
                </span>
                <span className="mt-1 block text-sm text-muted">{tier.example}</span>
                <span className="mt-2 block text-xs font-bold">
                  You get {money(payout)} · borrower gets {money(refund)} back
                </span>
              </label>
            );
          })}
        </div>
        <Field label="What happened?" hint="The borrower sees this. Be specific and factual.">
          <Textarea maxLength={2000} onChange={(e) => setNotes(e.target.value)} required value={notes} />
        </Field>
        {error && <Alert>{error}</Alert>}
        <div className="flex flex-wrap justify-between gap-3">
          <Link className="self-center text-sm font-bold underline" href={`/bookings/${booking.id}`}>
            Actually, the item is fine
          </Link>
          <Button busy={busy} disabled={!severity || !notes.trim()} type="submit" variant="danger">
            Submit damage report
          </Button>
        </div>
      </Card>
    </form>
  );
}

export default function DamagePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <PageShell width="max-w-4xl">
      <RequireAuth>
        {() => (
          <BookingStep eyebrow="Damage" id={id} title="Damage report">
            {(booking) =>
              booking.state === "settled" ? (
                <Outcome booking={booking} />
              ) : booking.available_actions.includes("report_damage") ? (
                <DamageForm booking={booking} />
              ) : (
                <WrongStep
                  booking={booking}
                  message={
                    booking.viewer_role === "borrower"
                      ? "Only the lender can report damage, after the item is returned."
                      : "Damage can be reported once the item has been returned."
                  }
                />
              )
            }
          </BookingStep>
        )}
      </RequireAuth>
    </PageShell>
  );
}
