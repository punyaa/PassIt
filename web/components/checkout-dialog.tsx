"use client";

import { useEffect, useId, useRef, useState } from "react";

import { Alert, Button, Field, Input } from "@/components/ui";
import { money } from "@/lib/format";

/** Optional payer details. Shown back to the user only; the mock gateway never needs them. */
export type PaymentDetails = { name: string; method: string; reference: string };

const METHODS: { value: string; label: string; icon: string }[] = [
  { value: "credit/debit card", label: "Credit / debit card", icon: "💳" },
  { value: "PayNow", label: "PayNow", icon: "🔳" },
  { value: "Apple Pay", label: "Apple Pay", icon: "📱" },
  { value: "cash at handover", label: "Cash at handover", icon: "💵" },
];

/** Mock payment portal between "Book now" and the booking: review, mark as paid or cancel. */
export function CheckoutDialog({
  open,
  onCancel,
  onMarkPaid,
  title,
  dates,
  fee,
  deposit,
  depositNote,
}: {
  open: boolean;
  onCancel: () => void;
  /** Creates the booking; rejects with a readable error if it could not be paid. */
  onMarkPaid: (details: PaymentDetails) => Promise<void>;
  title: string;
  dates: string;
  fee: number;
  deposit: number;
  depositNote?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const headingId = useId();
  const [details, setDetails] = useState<PaymentDetails>({ name: "", method: METHODS[0].value, reference: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const total = fee + deposit;

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setError(undefined);
      dialog.showModal();
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  async function markPaid() {
    setBusy(true);
    setError(undefined);
    try {
      await onMarkPaid(details);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Payment failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={ref}
      aria-labelledby={headingId}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onCancel();
      }}
      className="m-auto w-[min(30rem,calc(100vw-2rem))] rounded-card border border-line bg-white p-0 text-ink shadow-2xl backdrop:bg-ink/50"
    >
      <div className="p-6">
        <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-orange-deep">
          PassIt payment portal
        </p>
        <h2 id={headingId} className="mt-1 text-xl font-extrabold">
          Complete your payment
        </h2>

        <div className="mt-5 rounded-xl bg-forest-soft p-4 text-sm">
          <p className="font-extrabold">{title}</p>
          <p className="text-muted">{dates}</p>
          <dl className="mt-3 space-y-1.5">
            <div className="flex justify-between">
              <dt className="text-muted">Rental fee</dt>
              <dd className="font-bold">{money(fee)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">
                Refundable deposit
                {depositNote && (
                  <span className="ml-1 font-bold text-orange-deep">· {depositNote}</span>
                )}
              </dt>
              <dd className="font-bold">{money(deposit)}</dd>
            </div>
            <div className="flex justify-between border-t border-line pt-1.5 text-base">
              <dt className="font-extrabold">Amount due</dt>
              <dd className="font-extrabold">{money(total)}</dd>
            </div>
          </dl>
        </div>

        <fieldset className="mt-5" disabled={busy}>
          <legend className="text-sm font-extrabold">Pay by</legend>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {METHODS.map((method) => {
              const selected = details.method === method.value;
              return (
                <label
                  key={method.value}
                  className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-bold ${
                    selected ? "border-forest bg-forest-soft" : "border-line"
                  }`}
                >
                  <input
                    type="radio"
                    name="payment-method"
                    className="sr-only"
                    checked={selected}
                    onChange={() => setDetails({ ...details, method: method.value })}
                  />
                  <span aria-hidden="true">{method.icon}</span>
                  {method.label}
                </label>
              );
            })}
          </div>
        </fieldset>

        <fieldset className="mt-4 space-y-3" disabled={busy}>
          <legend className="text-sm font-extrabold">
            Payment details <span className="font-semibold text-muted">(optional)</span>
          </legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={details.method === "credit/debit card" ? "Name on card" : "Payer name"}>
              <Input
                autoComplete="name"
                placeholder="e.g. Ben Tan"
                value={details.name}
                onChange={(event) => setDetails({ ...details, name: event.target.value })}
              />
            </Field>
            <Field label={details.method === "credit/debit card" ? "Card last 4 digits" : "Reference"}>
              <Input
                inputMode={details.method === "credit/debit card" ? "numeric" : undefined}
                maxLength={details.method === "credit/debit card" ? 4 : 40}
                placeholder={details.method === "credit/debit card" ? "e.g. 4242" : "e.g. PayNow ref"}
                value={details.reference}
                onChange={(event) => setDetails({ ...details, reference: event.target.value })}
              />
            </Field>
          </div>
          <p className="text-xs text-muted">
            Mock payment: no real money moves and no full card numbers are collected.
          </p>
        </fieldset>

        {error && (
          <div className="mt-4">
            <Alert title="Payment failed">{error}</Alert>
          </div>
        )}

        <div className="mt-5 flex gap-3">
          <Button className="flex-1" variant="secondary" disabled={busy} onClick={onCancel}>
            Cancel payment
          </Button>
          <Button className="flex-1" variant="accent" busy={busy} onClick={() => void markPaid()}>
            {busy ? "Processing…" : "Mark as paid"}
          </Button>
        </div>
      </div>
    </dialog>
  );
}
