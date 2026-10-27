"use client";

import { NeedsAction } from "@/components/dashboard-bookings";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import {
  Alert,
  Card,
  LinkButton,
  PageHeader,
  Spinner,
  Stat,
} from "@/components/ui";
import type { Schemas } from "@/lib/api-client";
import { money } from "@/lib/format";
import { useApi } from "@/lib/use-api";

function BorrowerDashboard({ name }: { name: string }) {
  const dashboard = useApi<Schemas["Dashboard"]>("/dashboard?role=borrower");
  const d = dashboard.data;
  return (
    <>
      <PageHeader
        eyebrow="Borrower dashboard"
        title={`Hi ${name.split(" ")[0]}, here's what you saved`}
        actions={<LinkButton href="/search">Rent something</LinkButton>}
      />
      {dashboard.loading && <Spinner />}
      {dashboard.error && <Alert>{dashboard.error.message}</Alert>}
      {d && (
        <>
          <Card className="mb-6 bg-forest text-white">
            <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-[#d7edcc]">
              Estimated savings
            </p>
            <p className="mt-2 text-5xl font-extrabold tracking-[-0.05em]">
              {money(d.savings)}
            </p>
            <p className="mt-2 max-w-xl text-sm leading-6 text-[#ccdfd1]">
              Compared with buying each item, using the lender&apos;s deposit as
              a stand-in for its replacement value.
            </p>
          </Card>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Spent on rentals"
              value={money(d.total_spent)}
              hint="Fees plus any damage"
            />
            <Stat
              label="Deposits on hold"
              value={money(d.deposits_held)}
              hint="Refunded after return"
            />
            <Stat label="Active rentals" value={d.active_rentals} />
            <Stat label="Completed rentals" value={d.completed_rentals} />
          </div>
        </>
      )}
      <div className="mt-10">
        <NeedsAction role="borrower" compact={false} />
      </div>
    </>
  );
}

export default function BorrowerDashboardPage() {
  return (
    <PageShell>
      <RequireAuth>
        {(user) => <BorrowerDashboard name={user.display_name} />}
      </RequireAuth>
    </PageShell>
  );
}
