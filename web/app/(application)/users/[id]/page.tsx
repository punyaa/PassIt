"use client";

import { use } from "react";
import { Avatar } from "@/components/avatar";
import { CatalogueGrid } from "@/components/catalogue-grid";
import { PageShell } from "@/components/page-shell";
import { ProfileReviews } from "@/components/profile-reviews";
import { Alert, Button, Card, Spinner } from "@/components/ui";
import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

export default function PublicProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const profile = useApi<Schemas["PublicProfile"]>(`/users/${id}`);
  const user = profile.data;
  return (
    <PageShell>
      {profile.loading && <Spinner label="Loading profile…" />}
      {profile.error && (
        <Alert>
          {profile.error.message}{" "}
          <Button onClick={profile.reload} variant="secondary">
            Try again
          </Button>
        </Alert>
      )}
      {user && (
        <>
          <Card>
            <div className="flex items-center gap-5">
              <Avatar
                name={user.display_name}
                url={user.avatar_url}
                large={true}
              />
              <div className="min-w-0">
                <h1 className="text-3xl font-bold break-words">
                  {user.display_name}
                </h1>
                <p className="mt-2 text-sm text-muted">
                  Member since{" "}
                  {new Date(user.member_since).toLocaleDateString("en-SG", {
                    month: "long",
                    year: "numeric",
                  })}
                </p>
                <p className="mt-2 text-sm">
                  {user.rating !== null
                    ? `★ ${user.rating.toFixed(1)} · ${user.review_count} ${user.review_count === 1 ? "review" : "reviews"}`
                    : "No reviews yet"}
                </p>
              </div>
            </div>
            {user.bio && (
              <p className="mt-5 whitespace-pre-line break-words leading-7">
                {user.bio}
              </p>
            )}
          </Card>
          <section className="mt-9">
            <h2 className="mb-5 text-2xl font-bold">Available to rent</h2>
            <CatalogueGrid
              path={`/listings?owner_id=${id}&limit=50`}
              manage={false}
            />
          </section>
          <ProfileReviews userId={id} />
        </>
      )}
    </PageShell>
  );
}
