import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import { ListingEditor } from "./listing-editor";

export default async function EditListingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <PageShell width="max-w-3xl">
      <RequireAuth>
        <ListingEditor id={id} />
      </RequireAuth>
    </PageShell>
  );
}
