import Link from "next/link";

import { Brand } from "./brand";

export function MarketingHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-[#ece8df] bg-cream/95 backdrop-blur">
      <div className="mx-auto flex min-h-20 max-w-7xl items-center justify-between gap-3 px-4 sm:gap-6 sm:px-5 lg:px-8">
        <Brand href="/" />
        <nav className="hidden items-center gap-7 text-sm font-bold lg:flex" aria-label="Main navigation">
          <Link href="/search">Explore rentals</Link>
          <Link href="#how-it-works">How it works</Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link className="text-sm font-bold" href="/login">Log in</Link>
          <Link className="whitespace-nowrap rounded-xl bg-forest px-4 py-3 text-sm font-bold text-white" href="/listings/new">
            + List<span className="hidden sm:inline"> an item</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
