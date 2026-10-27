"use client";

import Link from "next/link";
import { CatalogueGrid } from "@/components/catalogue-grid";
import { PageShell } from "@/components/page-shell";
import { NeedsAction } from "@/components/dashboard-bookings";
import { useSession } from "@/components/session";
import { Button, Input, LinkButton } from "@/components/ui";
import { CATEGORIES } from "@/lib/catalogue";

export default function HomePage() {
  const { user } = useSession();
  return <PageShell width="max-w-7xl">
    <section className="home-intro">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-muted">Your neighbourhood, shared</p>
      <h1 className="mt-3 max-w-xl text-4xl font-extrabold tracking-[-0.05em] sm:text-5xl">A little borrowing.<br />A lot of possibilities.</h1>
      <p className="mt-4 text-muted">Find what you need, for as long as you need it.</p>
      <form action="/search" className="mt-6 flex max-w-2xl gap-2" role="search">
        <Input aria-label="Search rentals" name="q" placeholder="What would you like to rent?" type="search" />
        <Button type="submit">Search</Button>
      </form>
    </section>
    <section className="my-8" aria-label="Browse categories">
      <div className="category-grid">{CATEGORIES.map((category) => <Link href={`/search?category=${encodeURIComponent(category.name)}`} key={category.name} className="category-shortcut"><span aria-hidden="true" className="text-3xl">{category.icon}</span><span>{category.name}</span></Link>)}</div>
    </section>
    {user && <section className="mb-9 rounded-card border border-line bg-white p-5"><div className="mb-4 flex items-center justify-between gap-3"><h2 className="text-xl font-bold">Your rentals</h2><Link href="/bookings" className="text-sm font-bold underline">View all</Link></div><div className="grid gap-5 lg:grid-cols-2"><NeedsAction role="borrower" /><NeedsAction role="lender" /></div></section>}
    <section><div className="mb-5 flex items-center justify-between gap-3"><h2 className="text-2xl font-bold tracking-tight">Ready to rent</h2><LinkButton href="/search" variant="ghost">Browse all →</LinkButton></div><CatalogueGrid path="/listings?limit=12" manage={false} /></section>
  </PageShell>;
}
