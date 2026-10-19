import Link from "next/link";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-[#ece8df] bg-[#fffdf8]/95 backdrop-blur">
      <div className="mx-auto flex min-h-20 max-w-7xl items-center justify-between gap-6 px-5 lg:px-8">
        <Link className="flex items-center gap-3 text-2xl font-extrabold tracking-[-0.06em]" href="/">
          <span className="grid size-9 -rotate-6 place-items-center rounded-xl bg-[#f2a65f]">↗</span>
          <span>
            Pass<span className="text-[#d8793f]">It</span>
            <small className="block text-[8px] tracking-[0.22em] text-[#577364]">
              RENT • SHARE • REPEAT
            </small>
          </span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm font-bold md:flex" aria-label="Main navigation">
          <Link href="/search">Explore rentals</Link>
          <Link href="/#how-it-works">How it works</Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link className="text-sm font-bold" href="/login">
            Log in
          </Link>
          <Link className="rounded-xl bg-[#173f30] px-4 py-3 text-sm font-bold text-white" href="/listings/new">
            + List an item
          </Link>
        </div>
      </div>
    </header>
  );
}
