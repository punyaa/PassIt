import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";

import { ListingForm } from "./listing-form";

export default function NewListingPage() {
  return (
    <PageShell width="max-w-3xl">
      <RequireAuth>
        <ListingForm />
      </RequireAuth>
    </PageShell>
  );
}
