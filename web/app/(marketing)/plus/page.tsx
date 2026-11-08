import Link from "next/link";

import { PlanPerks } from "@/components/plan-perks";
import { applicationUrl } from "@/lib/application-url";
import type { PlusPlan } from "@/lib/auth";
import { PLAN_DETAILS } from "@/lib/plus-plans";

const TIERS: { name: string; plan: PlusPlan; cta: string }[] = [
  { name: "Eco Saver", plan: "saver", cta: "Start free" },
  { name: "Prime Saver", plan: "eco-saver", cta: "Become a Prime Saver" },
  { name: "Mega Saver", plan: "mega-saver", cta: "Become a Mega Saver" },
];

export default function PlusPage() {
  return (
    <main>
      <section className="mx-auto mt-7 max-w-7xl px-5 lg:px-8">
        <div className="rounded-3xl bg-forest px-7 py-14 text-white lg:px-14">
          <p className="text-xs font-extrabold tracking-[0.16em] text-sage">PASSIT PLUS MEMBERSHIP</p>
          <h1 className="mt-4 max-w-2xl text-4xl font-extrabold leading-tight tracking-[-0.04em] lg:text-5xl">
            Rent more, pay less, <span className="text-orange">worry never.</span>
          </h1>
          <p className="mt-4 max-w-xl leading-7 text-[#ccdfd1]">
            Borrowers pay lower or zero deposits. Lenders list more items and get paid faster.
            Pick the plan that matches how you use PassIt.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-14 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-3">
          {TIERS.map((tier) => {
            const details = PLAN_DETAILS[tier.plan];
            return (
              <article
                key={tier.name}
                className={`flex flex-col rounded-card border bg-white p-7 ${
                  details.featured ? "border-orange shadow-xl" : "border-line"
                }`}
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-extrabold">{tier.name}</h2>
                  {details.featured && (
                    <span className="rounded-full bg-orange px-3 py-1 text-xs font-extrabold text-ink">
                      MOST POPULAR
                    </span>
                  )}
                </div>
                <p className="mt-4">
                  <span className="text-4xl font-extrabold tracking-[-0.04em]">{details.price}</span>{" "}
                  <span className="text-sm font-bold text-muted">{details.cadence}</span>
                </p>
                <p className="mt-3 text-sm leading-6 text-muted">{details.tagline}</p>
                <div className="mt-6 flex-1">
                  <PlanPerks borrower={details.borrower} lender={details.lender} />
                </div>
                <Link
                  className={`mt-7 block rounded-xl px-5 py-3 text-center text-sm font-extrabold ${
                    details.featured ? "bg-orange text-ink" : "bg-forest text-white"
                  }`}
                  href={applicationUrl(`/signup?plan=${tier.plan}`)}
                >
                  {tier.cta}
                </Link>
              </article>
            );
          })}
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {[
            ["Cancel anytime", "Plus is month to month. Keep your bookings and reviews either way."],
            ["Deposits still protected", "Lower or zero deposits never change the photo evidence and fair settlement."],
            ["Lenders earn the same", "Membership perks are funded by PassIt, not taken from lender payouts."],
          ].map(([title, text]) => (
            <div key={title} className="rounded-card bg-sand p-6">
              <h3 className="font-extrabold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{text}</p>
            </div>
          ))}
        </div>

        <p className="mx-auto mt-10 max-w-2xl text-center text-xs leading-5 text-muted">
          PassIt Plus is a prototype preview: plans are not charged, and perks marked Soon are on
          the roadmap. Payments on PassIt are simulated throughout the prototype.
        </p>
      </section>
    </main>
  );
}
