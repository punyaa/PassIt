import type { PlusPlan } from "./auth";

/** One benefit line. `soon` marks perks that are announced but not enforced yet. */
export type Perk = { text: string; soon?: boolean };

export type PlanDetails = {
  price: string;
  cadence: string;
  tagline: string;
  featured?: boolean;
  borrower: Perk[];
  lender: Perk[];
};

// Keep in step with api/app/memberships/plans.py: deposits, listing limits and payout
// speed are enforced by the API; perks marked `soon` are roadmap items.
export const PLAN_DETAILS: Record<PlusPlan, PlanDetails> = {
  saver: {
    price: "S$0",
    cadence: "free forever",
    tagline: "Everyday renting and lending, free.",
    borrower: [
      { text: "Rent any item" },
      { text: "Standard refundable deposit" },
      { text: "Photo-checked handovers" },
    ],
    lender: [
      { text: "Up to 3 active listings" },
      { text: "0% commission" },
      { text: "AI price suggestions" },
    ],
  },
  "eco-saver": {
    price: "S$6.90",
    cadence: "per month",
    tagline: "For regulars: cheaper deposits and faster payouts.",
    featured: true,
    borrower: [
      { text: "25% lower deposits" },
      { text: "Free rescheduling", soon: true },
      { text: "Early access to new listings", soon: true },
    ],
    lender: [
      { text: "Up to 10 active listings" },
      { text: "Payouts in 3 days" },
      { text: "Prime badge on listings", soon: true },
    ],
  },
  "mega-saver": {
    price: "S$12.90",
    cadence: "per month",
    tagline: "Zero deposits, unlimited listings, same-day payouts.",
    borrower: [
      { text: "Zero deposits" },
      { text: "1 free delivery a month", soon: true },
      { text: "+1 day return grace", soon: true },
    ],
    lender: [
      { text: "Unlimited listings" },
      { text: "Same-day payouts" },
      { text: "Boosted in search", soon: true },
    ],
  },
};
