"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CatalogueGrid } from "@/components/catalogue-grid";
import { PageShell } from "@/components/page-shell";
import {
  RequireAuth,
  useSession,
  type SessionUser,
} from "@/components/session";
import { Alert, Button, Card, LinkButton, PageHeader } from "@/components/ui";
import { Avatar } from "@/components/avatar";
import { ProfileReviews } from "@/components/profile-reviews";

function Profile({ user }: { user: SessionUser }) {
  const { signOut } = useSession();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <>
      <PageHeader title="Your profile" />
      <Card className="flex flex-wrap items-center gap-5">
        <Avatar name={user.display_name} url={user.avatar_url} large={true} />
        <div className="min-w-0 basis-40 flex-1">
          <h2 className="text-2xl font-bold break-words">
            {user.display_name}
          </h2>
          <p className="mt-1 break-all text-muted">{user.email}</p>
          <p className="mt-2 text-xs text-muted">
            Your email is only visible to you.
          </p>
        </div>
        <Button
          busy={busy}
          variant="secondary"
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              await signOut();
              router.push("/home");
            } catch {
              setError("Couldn't log out. Please try again.");
            } finally {
              setBusy(false);
            }
          }}
        >
          Log out
        </Button>
        {error && <Alert>{error}</Alert>}
      </Card>
      {user.bio && (
        <p className="mt-4 whitespace-pre-line break-words leading-7">
          {user.bio}
        </p>
      )}
      <div className="mt-5 flex flex-wrap gap-3">
        <LinkButton href="/profile/edit">Edit profile</LinkButton>
        <LinkButton href={`/users/${user.user_id}`} variant="secondary">
          View public profile
        </LinkButton>
        <LinkButton href="/profile/saved" variant="secondary">
          Saved listings
        </LinkButton>
      </div>
      <section className="mt-9">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-2xl font-bold">My listings</h2>
          <div className="flex gap-2">
            <LinkButton href="/listings/manage" variant="secondary">
              Manage
            </LinkButton>
            <LinkButton href="/listings/new">+ List an item</LinkButton>
          </div>
        </div>
        <CatalogueGrid path="/listings/mine" manage={true} />
      </section>
      <section
        className="mt-9 grid gap-4 sm:grid-cols-2"
        aria-label="Rental insights"
      >
        <LinkButton
          className="justify-between border border-line bg-white p-6"
          href="/dashboard/lender"
          variant="secondary"
        >
          Your earnings <span aria-hidden="true">→</span>
        </LinkButton>
        <LinkButton
          className="justify-between border border-line bg-white p-6"
          href="/dashboard/borrower"
          variant="secondary"
        >
          Your savings <span aria-hidden="true">→</span>
        </LinkButton>
      </section>
      <ProfileReviews userId={user.user_id} />
    </>
  );
}

export default function ProfilePage() {
  return (
    <PageShell>
      <RequireAuth>{(user) => <Profile user={user} />}</RequireAuth>
    </PageShell>
  );
}
