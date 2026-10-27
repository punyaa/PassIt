"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CatalogueGrid } from "@/components/catalogue-grid";
import { PageShell } from "@/components/page-shell";
import { RequireAuth, useSession, type SessionUser } from "@/components/session";
import { Alert, Button, Card, EmptyState, LinkButton, PageHeader, Spinner } from "@/components/ui";
import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

function Profile({ user }: { user: SessionUser }) {
  const { signOut } = useSession();
  const router = useRouter();
  const reviews = useApi<Schemas["Review"][]>(`/reviews?user_id=${user.user_id}&limit=20`);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return <>
    <PageHeader title="Your profile" />
    <Card className="flex flex-wrap items-center gap-5">
      <span className="grid size-20 place-items-center rounded-full bg-sage text-3xl font-bold" aria-hidden="true">{user.display_name.split(" ").map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</span>
      <div className="min-w-0 flex-1"><h2 className="text-2xl font-bold">{user.display_name}</h2><p className="mt-1 break-all text-muted">{user.email}</p><p className="mt-2 text-xs text-muted">Your email is only visible to you.</p></div>
      <Button busy={busy} variant="secondary" onClick={async () => { setBusy(true); setError(null); try { await signOut(); router.push("/home"); } catch { setError("Couldn't log out. Please try again."); } finally { setBusy(false); } }}>Log out</Button>
      {error && <Alert>{error}</Alert>}
    </Card>
    <section className="mt-9"><div className="mb-5 flex flex-wrap items-center justify-between gap-3"><h2 className="text-2xl font-bold">My listings</h2><div className="flex gap-2"><LinkButton href="/listings/manage" variant="secondary">Manage</LinkButton><LinkButton href="/listings/new">+ List an item</LinkButton></div></div><CatalogueGrid path="/listings/mine" manage={true} /></section>
    <section className="mt-9 grid gap-4 sm:grid-cols-2" aria-label="Rental insights"><LinkButton className="justify-between border border-line bg-white p-6" href="/dashboard/lender" variant="secondary">Your earnings <span aria-hidden="true">→</span></LinkButton><LinkButton className="justify-between border border-line bg-white p-6" href="/dashboard/borrower" variant="secondary">Your savings <span aria-hidden="true">→</span></LinkButton></section>
    <section className="mt-9"><h2 className="mb-5 text-2xl font-bold">Received reviews</h2>{reviews.loading && <Spinner label="Loading reviews…" />}{reviews.error && <Alert>{reviews.error.message} <Button onClick={reviews.reload} variant="secondary">Try again</Button></Alert>}{reviews.data?.length === 0 && <EmptyState title="No reviews yet">Reviews from your rental partners will appear here.</EmptyState>}<div className="grid gap-4 sm:grid-cols-2">{reviews.data?.map((review) => <Card key={review.id}><p className="font-bold" aria-label={`${review.rating} out of 5 stars`}>{"★".repeat(review.rating)}</p>{review.comment && <p className="mt-3 leading-6">{review.comment}</p>}<p className="mt-3 text-sm text-muted">{review.author_display_name}</p></Card>)}</div></section>
  </>;
}

export default function ProfilePage() {
  return <PageShell><RequireAuth>{(user) => <Profile user={user} />}</RequireAuth></PageShell>;
}
