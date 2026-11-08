"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAccountData, useRentalReminders } from "./account-data";
import { meetupsAwaitingReply } from "./meetups";
import { Brand } from "./brand";
import { isPlusPlan, PLUS_PLAN_NAMES } from "@/lib/auth";
import { useSession } from "./session";

const links = [
  { href: "/home", label: "Home", path: "M3 10 12 3l9 7v11h-6v-7H9v7H3Z" },
  {
    href: "/search",
    label: "Search",
    path: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  },
  {
    href: "/bookings",
    label: "Rentals",
    path: "M5 5h14v16H5ZM8 2v6m8-6v6M5 11h14",
  },
  {
    href: "/meetings",
    label: "Meetings",
    path: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z",
  },
  {
    href: "/profile",
    label: "Profile",
    path: "M20 21v-2a8 8 0 0 0-16 0v2M16 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  },
] as const;

export function AppHeader() {
  const { user, loading } = useSession();
  const pathname = usePathname();
  const { reminders } = useRentalReminders();
  const replies = meetupsAwaitingReply(useAccountData().meetups.data).length;
  const badges: Record<string, { count: number; title: string }> = {
    Rentals: { count: reminders.length, title: "rental reminders" },
    Meetings: { count: replies, title: "meetup proposals waiting for you" },
  };
  const plan = user?.plan ?? null;
  const plusLabel =
    isPlusPlan(plan) && plan !== "saver"
      ? PLUS_PLAN_NAMES[plan]
      : "Become Plus";
  const active =
    pathname === "/"
      ? "/home"
      : /^\/(handover|returns|damage|reviews)/.test(pathname)
        ? "/bookings"
        : /^\/(profile|dashboard|listings\/manage|listings\/new)/.test(
              pathname,
            ) || pathname.endsWith("/edit")
          ? "/profile"
          : pathname.startsWith("/listings/") || pathname.startsWith("/users/")
            ? "/search"
            : pathname;
  function navigation(mobile: boolean) {
    return (
      <nav
        aria-label={mobile ? "Mobile navigation" : "Main navigation"}
        className={
          mobile ? "app-bottom-nav" : "hidden items-center gap-2 md:flex"
        }
      >
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active.startsWith(link.href) ? "page" : undefined}
            className="app-nav-link"
            aria-label={link.label}
            title={
              badges[link.label]?.count
                ? `${badges[link.label].count} ${badges[link.label].title}`
                : undefined
            }
          >
            <svg
              aria-hidden="true"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d={link.path} />
            </svg>
            <span>
              {link.label}
              {(badges[link.label]?.count ?? 0) > 0 && (
                <span
                  aria-hidden="true"
                  className="ml-1 rounded-full bg-orange px-1.5 py-0.5 text-[10px] text-ink"
                >
                  {badges[link.label].count}
                </span>
              )}
            </span>
          </Link>
        ))}
      </nav>
    );
  }
  return (
    <>
      <a href="#app-content" className="skip-link">
        Skip to content
      </a>
      <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-18 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <Brand href="/home" />
          {navigation(false)}
          <div className="flex items-center gap-4">
            {!loading && !user && (
              <Link className="text-sm font-bold" href="/login">
                Log in
              </Link>
            )}
            {!loading && (
              <Link
                aria-label={plusLabel}
                className="whitespace-nowrap rounded-xl bg-sand px-3 py-3 text-sm font-bold text-orange-deep"
                href={user ? "/membership" : "/plus"}
                title={plusLabel}
              >
                <span aria-hidden="true">👑</span>
                <span className="hidden sm:inline"> {plusLabel}</span>
              </Link>
            )}
            <Link
              className="whitespace-nowrap rounded-xl bg-forest px-4 py-3 text-sm font-bold text-white"
              href="/listings/new"
            >
              + List an item
            </Link>
          </div>
        </div>
      </header>
      {navigation(true)}
    </>
  );
}
