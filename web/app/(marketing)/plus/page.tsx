import Link from "next/link";

import { applicationUrl } from "@/lib/application-url";

type Tier = {
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  cta: string;
  plan: string;
  featured?: boolean;
  benefits: string[];
  excluded?: string[];
};

const TIERS: Tier[] = [
  {
    name: "Eco Saver",
    price: "S$0",
    cadence: "free forever",
    blurb: "Everyday renting, free. Everything you need to borrow from your neighbours.",
    cta: "Start renting free",
    plan: "saver",
    benefits: [
      "Unlimited browsing and booking",
      "Standard refundable deposits",
      "Handover and return photo evidence",
      "Ratings, reviews and rental reminders",
    ],
  },
  {
    name: "Prime Saver",
    price: "S$6.90",
    cadence: "per month",
    blurb: "For regular renters who want cheaper deposits and first pick of new listings.",
    cta: "Become a Prime Saver",
    plan: "eco-saver",
    featured: true,
    benefits: [
      "Everything in Eco Saver",
      "25% lower deposits on every booking",
      "Free rescheduling up to 24 hours before pickup",
      "Early access to new listings near you",
      "Priority support",
    ],
  },
  {
    name: "Mega Saver",
    price: "S$12.90",
    cadence: "per month",
    blurb: "Rent like you own it. Zero deposits, delivered to your door, zero stress.",
    cta: "Become a Mega Saver",
    plan: "mega-saver",
    benefits: [
      "Everything in Prime Saver",
      "Zero deposits on eligible items",
      "One free delivery every month",
      "Extra day of grace on every return",
      "Dedicated support line",
    ],
  },
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
            Plus members get lower deposits, free rescheduling, deliveries and first pick of new
            listings near their MRT station. Pick the plan that matches how often you borrow.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-14 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-3">
          {TIERS.map((tier) => (
            <article
              key={tier.name}
              className={`flex flex-col rounded-card border bg-white p-7 ${
                tier.featured ? "border-orange shadow-xl" : "border-line"
              }`}
            >
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-extrabold">{tier.name}</h2>
                {tier.featured && (
                  <span className="rounded-full bg-orange px-3 py-1 text-xs font-extrabold text-ink">
                    MOST POPULAR
                  </span>
                )}
              </div>
              <p className="mt-4">
                <span className="text-4xl font-extrabold tracking-[-0.04em]">{tier.price}</span>{" "}
                <span className="text-sm font-bold text-muted">{tier.cadence}</span>
              </p>
              <p className="mt-3 text-sm leading-6 text-muted">{tier.blurb}</p>
              <ul className="mt-6 flex-1 space-y-3 text-sm font-semibold">
                {tier.benefits.map((benefit) => (
                  <li key={benefit} className="flex gap-2">
                    <span className="font-extrabold text-success" aria-hidden>
                      ✓
                    </span>
                    {benefit}
                  </li>
                ))}
              </ul>
              <Link
                className={`mt-7 block rounded-xl px-5 py-3 text-center text-sm font-extrabold ${
                  tier.featured ? "bg-orange text-ink" : "bg-forest text-white"
                }`}
                href={applicationUrl(`/signup?plan=${tier.plan}`)}
              >
                {tier.cta}
              </Link>
            </article>
          ))}
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
          PassIt Plus is a prototype preview: plans are not charged and perks unlock as the
          membership backend lands. Payments on PassIt are simulated throughout the prototype.
        </p>
      </section>
    </main>
  );
}
