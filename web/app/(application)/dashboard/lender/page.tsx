"use client";

import { NeedsAction } from "@/components/dashboard-bookings";
import { ListingCard } from "@/components/listing-card";
import { MeetupSection } from "@/components/meetups";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import {
  Alert,
  EmptyState,
  LinkButton,
  PageHeader,
  Spinner,
  Stat,
} from "@/components/ui";
import type { Schemas } from "@/lib/api-client";
import { money } from "@/lib/format";
import { useApi } from "@/lib/use-api";

const FREE_LISTINGS = 3;

function LenderDashboard() {
  const dashboard = useApi<Schemas["Dashboard"]>("/dashboard?role=lender");
  const listings = useApi<Schemas["Listing"][]>("/listings/mine");
  const d = dashboard.data;
  const used =
    listings.data?.filter((l) => l.status !== "archived").length ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Lender dashboard"
        title="Your earnings"
        actions={
          used < FREE_LISTINGS ? (
            <LinkButton href="/listings/new" variant="accent">
              + List an item
            </LinkButton>
          ) : undefined
        }
      />
      {dashboard.loading && <Spinner />}
      {dashboard.error && <Alert>{dashboard.error.message}</Alert>}
      {d && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Earned"
            value={money(d.earnings)}
            hint="Released fees plus damage payouts"
          />
          <Stat
            label="Pending release"
            value={money(d.pending_release)}
            hint="Held until the hold period ends"
          />
          <Stat label="Active rentals" value={d.active_rentals} />
          <Stat label="Completed rentals" value={d.completed_rentals} />
        </div>
      )}

      <div className="mt-10">
        <NeedsAction role="lender" compact={false} />
      </div>

      <div className="mt-10">
        <MeetupSection role="lender" title="Meetup requests" />
      </div>

      <section className="mt-10">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-xl font-extrabold">Your listings</h2>
          <span className="text-sm text-muted">
            {used} of {FREE_LISTINGS} free listings used
          </span>
        </div>
        {listings.loading && <Spinner />}
        {listings.data?.length === 0 && (
          <EmptyState title="Nothing listed yet">
            <div className="mt-4">
              <LinkButton href="/listings/new">List your first item</LinkButton>
            </div>
          </EmptyState>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {listings.data?.map((listing) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      </section>
    </>
  );
}

export default function LenderDashboardPage() {
  return (
    <PageShell>
      <RequireAuth>{() => <LenderDashboard />}</RequireAuth>
    </PageShell>
  );
}
