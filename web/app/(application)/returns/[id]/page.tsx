"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, use } from "react";

import { BookingStep, WrongStep } from "@/components/booking-step-page";
import { ChecklistForm } from "@/components/checklist-form";
import { EvidenceCompare } from "@/components/evidence";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import { Spinner } from "@/components/ui";
import type { Schemas } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

function ReturnContent({ booking }: { booking: Schemas["Booking"] }) {
  const evidenceOnly = useSearchParams().get("view") === "evidence";
  const checklists = useApi<Schemas["ChecklistRecord"][]>(`/bookings/${booking.id}/checklists`);
  const evidence = checklists.data ? <EvidenceCompare checklists={checklists.data} /> : <Spinner />;

  if (evidenceOnly || !booking.available_actions.includes("return")) {
    return (
      <div className="space-y-6">
        {!evidenceOnly && <WrongStep booking={booking} message="This booking isn't ready for a return." />}
        {evidence}
      </div>
    );
  }
  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-lg font-extrabold">Condition at handover</h2>
        {evidence}
      </section>
      <ChecklistForm booking={booking} stage="return" />
    </div>
  );
}

export default function ReturnPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <PageShell width="max-w-4xl">
      <RequireAuth>
        {() => (
          <BookingStep eyebrow="Return" id={id} title="Return the item">
            {(booking) => (
              <Suspense>
                <ReturnContent booking={booking} />
              </Suspense>
            )}
          </BookingStep>
        )}
      </RequireAuth>
    </PageShell>
  );
}
