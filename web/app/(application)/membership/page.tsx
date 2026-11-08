"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { RequireAuth, useSession } from "@/components/session";
import { Alert, Button, Card, PageHeader, Spinner, Stat } from "@/components/ui";
import { ApiError, type Schemas } from "@/lib/api-client";
import { PLUS_PLAN_NAMES, isPlusPlan, setMyPlan, type PlusPlan } from "@/lib/auth";
import { useApi } from "@/lib/use-api";

type Membership = Schemas["MembershipResponse"];

const PLAN_BLURBS: Record<PlusPlan, string> = {
  saver: "Everyday renting, free.",
  "eco-saver": "Cheaper deposits and first pick of new listings.",
  "mega-saver": "Zero deposits, a monthly delivery, extra return grace.",
};

function depositLabel(factor: string): string {
  if (factor === "0.00") return "Zero deposits";
  if (factor === "0.75") return "25% lower deposits";
  return "Standard deposits";
}

function periodLabel(membership: Membership | undefined): string {
  if (!membership?.current_period_end) return "Free forever";
  return `Renews ${new Date(membership.current_period_end).toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })}`;
}

function MembershipView() {
  const { refresh } = useSession();
  const requested = useSearchParams().get("plan");
  const highlight = isPlusPlan(requested) ? requested : undefined;
  const membership = useApi<Membership>("/memberships/me");
  const [busy, setBusy] = useState<PlusPlan | null>(null);
  const [error, setError] = useState<string>();

  if (membership.loading) return <Spinner label="Loading your membership…" />;
  if (membership.error && membership.error.status !== 404) {
    return <Alert>{membership.error.message}</Alert>;
  }
  // 404 means a pre-membership account: Eco Saver, free forever.
  const current: PlusPlan = membership.data?.plan ?? "saver";

  async function choose(plan: PlusPlan) {
    setBusy(plan);
    setError(undefined);
    try {
      membership.setData(await setMyPlan(plan));
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="PassIt Plus"
        title="Your membership"
        description="Deposits, rescheduling and deliveries follow your plan automatically on every booking."
      />
      {highlight && highlight !== current && (
        <Alert>
          You picked {PLUS_PLAN_NAMES[highlight]} — confirm below to switch. Plan changes are
          simulated, no charge.
        </Alert>
      )}
      {membership.data?.status === "expired" && (
        <Alert>Your paid period ended — you&apos;re on Eco Saver until you pick a plan.</Alert>
      )}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {(Object.keys(PLAN_BLURBS) as PlusPlan[]).map((plan) => {
          const isCurrent = plan === current;
          const perks = plan === current ? membership.data?.perks : undefined;
          return (
            <Card key={plan} className={highlight === plan && !isCurrent ? "border-orange" : ""}>
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-extrabold">{PLUS_PLAN_NAMES[plan]}</h2>
                {isCurrent && (
                  <span className="rounded-full bg-forest px-3 py-1 text-xs font-extrabold text-white">
                    CURRENT
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">{PLAN_BLURBS[plan]}</p>
              <p className="mt-3 text-sm font-bold">
                {perks ? depositLabel(perks.deposit_factor) : depositLabel(plan === "eco-saver" ? "0.75" : plan === "mega-saver" ? "0.00" : "1.00")}
              </p>
              <p className="mt-1 text-sm text-muted">
                {isCurrent ? periodLabel(membership.data) : plan === "saver" ? "Free forever" : "30-day periods"}
              </p>
              <div className="mt-5">
                {isCurrent ? (
                  <Button className="w-full" disabled>
                    Current plan
                  </Button>
                ) : (
                  <Button
                    busy={busy === plan}
                    className="w-full"
                    onClick={() => void choose(plan)}
                  >
                    Switch to {PLUS_PLAN_NAMES[plan]}
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
      {error && (
        <div className="mt-4">
          <Alert>{error}</Alert>
        </div>
      )}
      {membership.data && (
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <Stat
            label="Rescheduling"
            value={membership.data.perks.free_rescheduling ? "Free" : "Standard"}
            hint="Cancel and rebook before pickup"
          />
          <Stat
            label="Delivery credits"
            value={membership.data.perks.delivery_credits}
            hint="Free deliveries per period"
          />
          <Stat
            label="Return grace"
            value={membership.data.perks.grace_days === 1 ? "1 day" : `${membership.data.perks.grace_days} days`}
            hint="Extra time on every return"
          />
        </div>
      )}
    </>
  );
}

export default function MembershipPage() {
  return (
    <PageShell>
      <RequireAuth>
        <Suspense>
          <MembershipView />
        </Suspense>
      </RequireAuth>
    </PageShell>
  );
}
