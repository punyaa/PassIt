"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brand } from "./brand";
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
    href: "/profile",
    label: "Profile",
    path: "M20 21v-2a8 8 0 0 0-16 0v2M16 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  },
] as const;

export function AppHeader() {
  const { user, loading } = useSession();
  const pathname = usePathname();
  const active =
    pathname === "/"
      ? "/home"
      : /^\/(handover|returns|damage|reviews)/.test(pathname)
        ? "/bookings"
        : /^\/(profile|dashboard|listings\/manage|listings\/new)/.test(
              pathname,
            ) || pathname.endsWith("/edit")
          ? "/profile"
          : pathname.startsWith("/listings/")
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
            <span>{link.label}</span>
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
            <Link
              className="rounded-xl bg-forest px-4 py-3 text-sm font-bold text-white"
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
