import type { Perk } from "@/lib/plus-plans";

function PerkList({ title, perks }: { title: string; perks: Perk[] }) {
  return (
    <div>
      <h3 className="text-xs font-extrabold uppercase tracking-[0.14em] text-orange-deep">
        {title}
      </h3>
      <ul className="mt-2 space-y-2 text-sm font-semibold">
        {perks.map((perk) => (
          <li key={perk.text} className="flex items-start gap-2">
            <span className="font-extrabold text-success" aria-hidden="true">
              ✓
            </span>
            <span className={perk.soon ? "text-muted" : undefined}>
              {perk.text}
              {perk.soon && (
                <span className="ml-2 rounded-full bg-sand px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-muted">
                  Soon
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Borrower and lender benefits of one Plus plan, shared by /plus and /membership. */
export function PlanPerks({ borrower, lender }: { borrower: Perk[]; lender: Perk[] }) {
  return (
    <div className="space-y-5">
      <PerkList title="For borrowers" perks={borrower} />
      <PerkList title="For lenders" perks={lender} />
    </div>
  );
}
