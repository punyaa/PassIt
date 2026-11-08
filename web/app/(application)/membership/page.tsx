"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { PageShell } from "@/components/page-shell";
import { RequireAuth, useSession } from "@/components/session";
import { Alert, Button, Card, PageHeader, Spinner, Stat } from "@/components/ui";
import { ApiError, type Schemas } from "@/lib/api-client";
import { PlanPerks } from "@/components/plan-perks";
import { PLUS_PLAN_NAMES, isPlusPlan, setMyPlan, type PlusPlan } from "@/lib/auth";
import { PLAN_DETAILS } from "@/lib/plus-plans";
import { useApi } from "@/lib/use-api";

type Membership = Schemas["MembershipResponse"];

const PLAN_ORDER: PlusPlan[] = ["saver", "eco-saver", "mega-saver"];

function depositLabel(factor: string): string {
  if (factor === "0.00") return "Zero deposits";
  if (factor === "0.75") return "25% lower deposits";
  return "Standard deposits";
}

// What each plan promises. Staging shortens every hold to a minute so demos show a release,
// so the label comes from the plan rather than from the effective hold.
const DEPOSIT_LABELS: Record<PlusPlan, string> = {
  saver: "Standard deposits",
  "eco-saver": "25% lower deposits",
  "mega-saver": "Zero deposits",
};

const LISTING_LABELS: Record<PlusPlan, string> = {
  saver: "Up to 3",
  "eco-saver": "Up to 10",
  "mega-saver": "Unlimited",
};

const PAYOUT_LABELS: Record<PlusPlan, string> = {
  saver: "7 days",
  "eco-saver": "3 days",
  "mega-saver": "Same day",
};

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
  const perks = membership.data?.perks;

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
        description="Your plan sets your deposit when you borrow, and your listing limit and payout speed when you lend. Plan changes are simulated: no charge."
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
        {PLAN_ORDER.map((plan) => {
          const isCurrent = plan === current;
          const details = PLAN_DETAILS[plan];
          return (
            <Card
              key={plan}
              className={`flex flex-col ${
                highlight === plan && !isCurrent
                  ? "border-orange"
                  : details.featured
                    ? "border-orange/60"
                    : ""
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-xl font-extrabold">{PLUS_PLAN_NAMES[plan]}</h2>
                {isCurrent ? (
                  <span className="rounded-full bg-forest px-3 py-1 text-xs font-extrabold text-white">
                    CURRENT
                  </span>
                ) : (
                  details.featured && (
                    <span className="rounded-full bg-orange px-3 py-1 text-xs font-extrabold text-ink">
                      MOST POPULAR
                    </span>
                  )
                )}
              </div>
              <p className="mt-3">
                <span className="text-3xl font-extrabold tracking-[-0.04em]">{details.price}</span>{" "}
                <span className="text-sm font-bold text-muted">{details.cadence}</span>
              </p>
              <p className="mt-2 text-sm leading-6 text-muted">{details.tagline}</p>
              <div className="mt-5 flex-1">
                <PlanPerks borrower={details.borrower} lender={details.lender} />
              </div>
              <p className="mt-5 text-xs font-bold text-muted">
                {isCurrent ? periodLabel(membership.data) : plan === "saver" ? "Free forever" : "30-day periods"}
              </p>
              <div className="mt-3">
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
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Stat
          label="Your deposit"
          value={perks ? depositLabel(perks.deposit_factor) : DEPOSIT_LABELS[current]}
          hint="Applied automatically when you book"
        />
        <Stat
          label="Your listings"
          value={
            perks
              ? perks.listing_limit == null
                ? "Unlimited"
                : `Up to ${perks.listing_limit}`
              : LISTING_LABELS[current]
          }
          hint="Active listings you can have as a lender"
        />
        <Stat
          label="Your payouts"
          value={PAYOUT_LABELS[current]}
          hint="Rental fee released after handover"
        />
      </div>
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
