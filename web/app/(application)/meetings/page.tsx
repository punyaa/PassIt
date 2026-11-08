"use client";

import { useState } from "react";

import { useAccountData } from "@/components/account-data";
import { awaitingMe, isUpcoming, MeetupCard } from "@/components/meetups";
import { PageShell } from "@/components/page-shell";
import { RequireAuth } from "@/components/session";
import {
  Alert,
  Button,
  EmptyState,
  LinkButton,
  PageHeader,
  Spinner,
} from "@/components/ui";
import type { Schemas } from "@/lib/api-client";

type Tab = "upcoming" | "negotiating" | "past";

const tabs: { id: Tab; label: string; empty: string }[] = [
  { id: "upcoming", label: "Upcoming", empty: "No meetings scheduled yet" },
  { id: "negotiating", label: "Negotiating", empty: "No open proposals" },
  { id: "past", label: "Past & closed", empty: "Nothing here yet" },
];

function group(meetups: Schemas["Meetup"][]): Record<Tab, Schemas["Meetup"][]> {
  const upcoming = meetups
    .filter((m) => m.status === "accepted" && isUpcoming(m))
    .sort((a, b) => a.meet_at.localeCompare(b.meet_at));
  const negotiating = meetups
    .filter((m) => m.status === "pending")
    .sort((a, b) => Number(awaitingMe(b)) - Number(awaitingMe(a)));
  const past = meetups.filter(
    (m) => !upcoming.includes(m) && !negotiating.includes(m),
  );
  return { upcoming, negotiating, past };
}

function Meetings() {
  const { meetups } = useAccountData();
  const [tab, setTab] = useState<Tab>();
  const groups = group(meetups.data ?? []);
  // Open on whatever needs the person first: a reply, then the next meeting.
  const current =
    tab ??
    (groups.negotiating.some(awaitingMe)
      ? "negotiating"
      : groups.upcoming.length
        ? "upcoming"
        : "negotiating");
  const shown = groups[current];

  return (
    <>
      <PageHeader
        eyebrow="Meetings"
        title="Your meetups"
        description="Agree on when, where and how much with the other person. Once you both accept, the meeting is scheduled here."
        actions={
          <LinkButton href="/search" variant="secondary">
            Find something to borrow
          </LinkButton>
        }
      />
      {meetups.data && (
        <div
          aria-label="Meeting groups"
          className="mb-6 flex flex-wrap gap-2"
          role="tablist"
        >
          {tabs.map(({ id, label }) => {
            const replies =
              id === "negotiating"
                ? groups.negotiating.filter(awaitingMe).length
                : 0;
            return (
              <button
                aria-selected={current === id}
                className={`rounded-full border px-4 py-2 text-sm font-bold transition ${
                  current === id
                    ? "border-forest bg-forest text-white"
                    : "border-line bg-white hover:bg-sand"
                }`}
                key={id}
                onClick={() => setTab(id)}
                role="tab"
                type="button"
              >
                {label} ({groups[id].length})
                {replies > 0 && (
                  <span className="ml-2 rounded-full bg-orange px-1.5 py-0.5 text-[10px] text-ink">
                    {replies} to answer
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
      {meetups.loading && !meetups.data && (
        <Spinner label="Loading meetings…" />
      )}
      {meetups.error && (
        <Alert>
          {meetups.error.message}{" "}
          <Button onClick={meetups.reload} variant="secondary">
            Try again
          </Button>
        </Alert>
      )}
      {meetups.data && shown.length === 0 && (
        <EmptyState title={tabs.find((t) => t.id === current)!.empty}>
          Open any listing and choose <strong>Propose a meetup</strong> to
          suggest a time, place and price.
        </EmptyState>
      )}
      <div className="space-y-4" role="tabpanel">
        {shown.map((meetup) => (
          <MeetupCard
            key={meetup.id}
            meetup={meetup}
            onChange={meetups.reload}
          />
        ))}
      </div>
    </>
  );
}

export default function MeetingsPage() {
  return (
    <PageShell width="max-w-3xl">
      <RequireAuth>
        <Meetings />
      </RequireAuth>
    </PageShell>
  );
}
