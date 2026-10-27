import { Suspense } from "react";

import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";

import { BookingList } from "./booking-list";

export default function BookingsPage() {
  return (
    <PageShell width="max-w-4xl">
      <RequireAuth>
        <Suspense>
          <BookingList />
        </Suspense>
      </RequireAuth>
    </PageShell>
  );
}
