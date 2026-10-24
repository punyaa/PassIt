import { Suspense } from "react";

import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";

import { BookingView } from "./booking-view";

export default async function BookingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <PageShell width="max-w-5xl">
      <RequireAuth>
        <Suspense>
          <BookingView id={id} />
        </Suspense>
      </RequireAuth>
    </PageShell>
  );
}
