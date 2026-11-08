"use client";

import { useEffect } from "react";

import { Card, Spinner } from "@/components/ui";
import type { Schemas } from "@/lib/api-client";
import { formatDateTime, money } from "@/lib/format";
import { useApi } from "@/lib/use-api";

type Payment = Schemas["BookingPaymentResponse"];
type Operation = Payment["operations"][number];

const STATUS: Record<Payment["status"], { label: string; className: string }> = {
  captured: { label: "Paid", className: "bg-success-soft text-success" },
  partially_refunded: { label: "Partly refunded", className: "bg-sand text-orange-deep" },
  refunded: { label: "Refunded", className: "bg-sand text-muted" },
  failed: { label: "Failed", className: "bg-danger-soft text-danger" },
  cancelled: { label: "Cancelled", className: "bg-sand text-muted" },
};

function operationLabel(operation: Operation, viewer: "borrower" | "lender"): string {
  if (operation.operation === "charge") return viewer === "borrower" ? "Charged to you" : "Borrower charged";
  if (operation.operation === "refund") return viewer === "borrower" ? "Refunded to you" : "Refunded to borrower";
  return viewer === "lender" ? "Paid out to you" : "Paid out to lender";
}

/** The mock gateway's own record of a booking's payment: method, status and every
 * charge, refund and payout it processed. Complements the ledger card. */
export function PaymentCard({
  bookingId,
  viewer,
  version,
}: {
  bookingId: string;
  viewer: "borrower" | "lender";
  version: string;
}) {
  const payment = useApi<Payment>(`/payments/bookings/${bookingId}`);
  const { reload } = payment;
  // Refunds and payouts happen as the booking moves on: refetch when it changes.
  useEffect(() => {
    reload();
  }, [version, reload]);

  if (payment.error?.status === 404) return null; // bookings made before the gateway
  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-extrabold">Payment</h2>
        {payment.data && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-extrabold ${STATUS[payment.data.status].className}`}
          >
            {STATUS[payment.data.status].label}
          </span>
        )}
      </div>
      <p className="mb-3 text-xs text-muted">PassIt mock gateway: no real card is charged.</p>
      {payment.error ? (
        <p className="text-sm text-muted">{payment.error.message}</p>
      ) : !payment.data ? (
        <Spinner />
      ) : (
        <>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Method</dt>
              <dd className="text-right font-bold">{payment.data.payment_method_label}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Amount charged</dt>
              <dd className="font-bold">{money(payment.data.amount)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Reference</dt>
              <dd
                className="truncate font-mono text-xs"
                title={payment.data.provider_reference}
              >
                {payment.data.provider_reference}
              </dd>
            </div>
          </dl>
          <ol className="mt-4 space-y-3 border-t border-line pt-4 text-sm">
            {payment.data.operations.map((operation) => (
              <li key={operation.id} className="flex justify-between gap-3">
                <div>
                  <p className="font-bold">
                    {operationLabel(operation, viewer)}
                    {operation.status === "failed" && (
                      <span className="ml-2 text-xs font-extrabold text-danger">FAILED</span>
                    )}
                  </p>
                  <p className="text-xs text-muted">{formatDateTime(operation.created_at)}</p>
                </div>
                <p className="font-bold">{money(operation.amount)}</p>
              </li>
            ))}
          </ol>
        </>
      )}
    </Card>
  );
}
