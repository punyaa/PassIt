import { Suspense } from "react";

import { PageShell } from "@/components/page-shell";

import { SearchView } from "./search-view";

export default function SearchPage() {
  return (
    <PageShell width="max-w-7xl">
      <Suspense>
        <SearchView />
      </Suspense>
    </PageShell>
  );
}
