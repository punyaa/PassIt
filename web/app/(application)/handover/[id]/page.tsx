"use client";

import { use } from "react";

import { BookingStep, WrongStep } from "@/components/booking-step-page";
import { ChecklistForm } from "@/components/checklist-form";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";

export default function HandoverPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <PageShell width="max-w-3xl">
      <RequireAuth>
        {() => (
          <BookingStep eyebrow="Handover" id={id} title="Hand over the item">
            {(booking) =>
              booking.available_actions.includes("handover") ? (
                <ChecklistForm booking={booking} stage="handover" />
              ) : (
                <WrongStep booking={booking} message="This booking isn't ready for handover." />
              )
            }
          </BookingStep>
        )}
      </RequireAuth>
    </PageShell>
  );
}
