"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useSession } from "./session";

const links = [
  { href: "/search", label: "Explore rentals" },
  { href: "/bookings", label: "My bookings", auth: true },
  { href: "/dashboard/borrower", label: "Savings", auth: true },
  { href: "/dashboard/lender", label: "Earnings", auth: true },
];

export function AppHeader() {
  const { user, loading, signOut } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const visible = links.filter((link) => !link.auth || user);

  const navLink = (link: (typeof links)[number]) => (
    <Link
      aria-current={pathname.startsWith(link.href) ? "page" : undefined}
      className="aria-[current=page]:text-orange-deep"
      href={link.href}
      key={link.href}
      onClick={() => setOpen(false)}
    >
      {link.label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-20 border-b border-[#ece8df] bg-cream/95 backdrop-blur">
      <div className="mx-auto flex min-h-20 max-w-7xl items-center justify-between gap-3 px-4 sm:gap-6 sm:px-5 lg:px-8">
        <Link className="flex items-center gap-3 text-2xl font-extrabold tracking-[-0.06em]" href="/">
          <span className="grid size-9 -rotate-6 place-items-center rounded-xl bg-orange">↗</span>
          <span>
            Pass<span className="text-[#d8793f]">It</span>
            <small className="block text-[8px] tracking-[0.22em] text-[#577364]">RENT • SHARE • REPEAT</small>
          </span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm font-bold lg:flex" aria-label="Main navigation">
          {visible.map(navLink)}
        </nav>
        <div className="flex items-center gap-3">
          {!loading && !user && (
            <Link className="hidden text-sm font-bold sm:inline" href="/login">
              Log in
            </Link>
          )}
          {user && (
            <span className="hidden items-center gap-2 text-sm font-bold sm:flex">
              <span className="grid size-8 place-items-center rounded-full bg-sage text-xs">
                {user.display_name.slice(0, 1).toUpperCase()}
              </span>
              {user.display_name.split(" ")[0]}
              <button
                className="ml-1 text-xs font-bold text-muted underline"
                onClick={async () => {
                  await signOut();
                  router.push("/");
                }}
                type="button"
              >
                Log out
              </button>
            </span>
          )}
          <Link className="whitespace-nowrap rounded-xl bg-forest px-4 py-3 text-sm font-bold text-white" href="/listings/new">
            + List<span className="hidden sm:inline"> an item</span>
          </Link>
          <button
            aria-expanded={open}
            aria-label="Menu"
            className="rounded-xl border border-line px-3 py-2 text-sm font-bold lg:hidden"
            onClick={() => setOpen((value) => !value)}
            type="button"
          >
            ☰
          </button>
        </div>
      </div>
      {open && (
        <nav className="flex flex-col gap-4 border-t border-line px-5 py-4 text-sm font-bold lg:hidden" aria-label="Mobile navigation">
          {visible.map(navLink)}
          {!user && <Link href="/login">Log in</Link>}
        </nav>
      )}
    </header>
  );
}
