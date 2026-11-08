"use client";
import { CatalogueGrid } from "@/components/catalogue-grid";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import { LinkButton, PageHeader } from "@/components/ui";

export default function ManageListingsPage() {
  return (
    <PageShell>
      <RequireAuth>
        <PageHeader
          eyebrow="Profile"
          title="Manage listings"
          description="Update details, prices and open dates. Open a listing to manage it."
          actions={<LinkButton href="/listings/new">+ List an item</LinkButton>}
        />
        <CatalogueGrid path="/listings/mine" manage={true} />
      </RequireAuth>
    </PageShell>
  );
}
