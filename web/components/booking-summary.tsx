import Link from "next/link";

import type { Schemas } from "@/lib/api-client";
import { dateRange, money } from "@/lib/format";

import { BookingStateBadge } from "./booking-state";

export function BookingRow({ booking }: { booking: Schemas["Booking"] }) {
  return (
    <Link
      className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-line bg-white p-5 transition hover:shadow-md"
      href={`/bookings/${booking.id}`}
    >
      <div>
        <div className="flex items-center gap-3">
          <strong className="text-lg">{booking.listing_title}</strong>
          <BookingStateBadge state={booking.state} />
        </div>
        <p className="mt-1 text-sm text-muted">
          {dateRange(booking.start_date, booking.end_date)} · {booking.viewer_role === "borrower" ? "You're renting" : "You're lending"}
        </p>
      </div>
      <div className="text-right">
        <p className="font-extrabold">{money(booking.fee)}</p>
        {booking.available_actions.length > 0 && (
          <p className="text-xs font-bold text-orange-deep">Action needed →</p>
        )}
      </div>
    </Link>
  );
}

/** Totals derived from the ledger: what the borrower paid and got back, what the lender received. */
export function settlement(entries: Schemas["LedgerEntry"][]) {
  const sum = (account: string, ...types: string[]) =>
    entries
      .filter((e) => e.account === account && types.includes(e.entry_type))
      .reduce((total, e) => total + Number(e.amount), 0);
  return {
    feeReleased: sum("lender", "release_fee"),
    damagePaid: sum("lender", "damage_payout"),
    depositRefunded: sum("borrower", "refund_deposit"),
    heldNow: sum("platform_hold", "hold_fee", "hold_deposit", "release_fee", "refund_deposit", "damage_payout"),
  };
}

const ENTRY_LABELS: Record<Schemas["LedgerEntry"]["entry_type"], string> = {
  hold_fee: "Rental fee",
  hold_deposit: "Deposit",
  release_fee: "Fee released",
  refund_deposit: "Deposit refund",
  damage_payout: "Damage payout",
};

export function LedgerTable({ entries, role }: { entries: Schemas["LedgerEntry"][]; role: "borrower" | "lender" }) {
  const mine = entries.filter((e) => e.account === role);
  if (!mine.length) return <p className="text-sm text-muted">No money has moved for you yet.</p>;
  return (
    <table className="w-full text-sm">
      <tbody>
        {mine.map((entry, index) => {
          const amount = Number(entry.amount);
          const label =
            entry.entry_type.startsWith("hold") && amount > 0 ? `${ENTRY_LABELS[entry.entry_type]} returned` : ENTRY_LABELS[entry.entry_type];
          return (
            <tr className="border-b border-line last:border-0" key={`${entry.entry_type}-${index}`}>
              <td className="py-2">{label}</td>
              <td className={`py-2 text-right font-bold ${amount < 0 ? "text-danger" : "text-success"}`}>
                {amount < 0 ? "−" : "+"}
                {money(Math.abs(amount))}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
