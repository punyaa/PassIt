"use client";
import { useRentalReminders } from "./account-data";
import { BookingRow } from "./booking-summary";
import { Alert, Button, LinkButton, Spinner } from "./ui";

export function RentalReminders() {
  const rentals = useRentalReminders();
  return (
    <section className="mb-9 rounded-card border border-line bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">
          Rental reminders{" "}
          {rentals.reminders.length > 0 && `(${rentals.reminders.length})`}
        </h2>
        <LinkButton href="/bookings" variant="ghost">
          View rentals →
        </LinkButton>
      </div>
      {rentals.loading && !rentals.data && (
        <Spinner label="Checking your rentals…" />
      )}
      {rentals.error && (
        <Alert>
          {rentals.error.message}
          <Button onClick={rentals.reload} variant="secondary">
            Try again
          </Button>
        </Alert>
      )}
      {!rentals.loading && !rentals.error && rentals.reminders.length === 0 && (
        <p className="text-sm text-muted">
          No pickups, returns or actions due soon.
        </p>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {rentals.reminders.slice(0, 4).map(({ booking, label }) => (
          <div key={booking.id}>
            <p className="mb-2 text-sm font-bold text-orange-deep">{label}</p>
            <BookingRow booking={booking} />
          </div>
        ))}
      </div>
    </section>
  );
}
