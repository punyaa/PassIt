import { Suspense } from "react";

import { PageShell } from "@/components/page-shell";

import { ListingView } from "./listing-view";

export default async function ListingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <PageShell width="max-w-6xl">
      <Suspense>
        <ListingView id={id} />
      </Suspense>
    </PageShell>
  );
}
