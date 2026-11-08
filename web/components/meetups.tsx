"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { apiPost, type Schemas } from "@/lib/api-client";
import { money } from "@/lib/format";

import { useAccountData } from "./account-data";
import { useSession } from "./session";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Spinner,
  Textarea,
} from "./ui";

type Meetup = Schemas["Meetup"];
type MeetupEvent = Schemas["MeetupEvent"];
export type MeetupTermsInput = {
  meet_at: string;
  location: string;
  price: string;
  message: string;
};

const when = new Intl.DateTimeFormat("en-SG", {
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
});

export function formatMeetingTime(iso: string): string {
  return when.format(new Date(iso));
}

/** `<input type="datetime-local">` speaks local wall-clock time without an offset. */
function toLocalInput(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function defaultTime(): string {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(18, 0, 0, 0);
  return toLocalInput(date);
}

export const isUpcoming = (m: Meetup) =>
  new Date(m.meet_at).getTime() > Date.now();
export const awaitingMe = (m: Meetup) =>
  m.status === "pending" && m.awaiting_role === m.viewer_role;

/** Open proposals where it is the viewer's turn to accept, counter or decline. */
export function meetupsAwaitingReply(meetups: Meetup[] | undefined): Meetup[] {
  return meetups?.filter(awaitingMe) ?? [];
}

function errorText(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback;
}

export function MeetupTermsForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial: { meet_at?: string; location?: string; price?: string };
  submitLabel: string;
  onSubmit: (terms: MeetupTermsInput) => Promise<void>;
  onCancel?: () => void;
}) {
  const [meetAt, setMeetAt] = useState(
    initial.meet_at && new Date(initial.meet_at) > new Date()
      ? toLocalInput(new Date(initial.meet_at))
      : defaultTime(),
  );
  const [location, setLocation] = useState(initial.location ?? "");
  const [price, setPrice] = useState(initial.price ?? "");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const inFuture = meetAt !== "" && new Date(meetAt).getTime() > Date.now();
  const validPrice = price !== "" && Number(price) >= 0;
  const valid = inFuture && location.trim() !== "" && validPrice;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit({
        meet_at: new Date(meetAt).toISOString(),
        location: location.trim(),
        price: Number(price).toFixed(2),
        message: message.trim(),
      });
    } catch (caught) {
      setError(errorText(caught, "Couldn't send that. Try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-3" onSubmit={submit}>
      <Field
        label="Date & time"
        error={meetAt && !inFuture ? "Pick a time in the future." : undefined}
      >
        <Input
          min={toLocalInput(new Date())}
          onChange={(e) => setMeetAt(e.target.value)}
          required
          type="datetime-local"
          value={meetAt}
        />
      </Field>
      <Field
        label="Meeting point"
        hint="A public spot, e.g. an MRT exit or mall entrance."
      >
        <Input
          maxLength={200}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Clementi MRT, exit A"
          required
          value={location}
        />
      </Field>
      <Field
        label="Price (S$)"
        hint="The total you're agreeing to for this rental."
      >
        <Input
          inputMode="decimal"
          min="0"
          onChange={(e) => setPrice(e.target.value)}
          required
          step="0.01"
          type="number"
          value={price}
        />
      </Field>
      <Field label="Message (optional)">
        <Textarea
          className="min-h-20"
          maxLength={500}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Anything the other person should know"
          value={message}
        />
      </Field>
      {error && <Alert>{error}</Alert>}
      <div className="flex flex-wrap gap-3">
        <Button busy={busy} disabled={!valid} type="submit">
          {submitLabel}
        </Button>
        {onCancel && (
          <Button onClick={onCancel} type="button" variant="ghost">
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

/** Listing page: the borrower opens a negotiation with the lender. */
export function ProposeMeetup({
  listing,
}: {
  listing: Schemas["ListingDetail"];
}) {
  const { user } = useSession();
  const { meetups } = useAccountData();
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);

  if (listing.status !== "active") return null;
  const existing = meetups.data?.find(
    (m) =>
      m.listing_id === listing.id &&
      m.viewer_role === "borrower" &&
      m.status === "pending",
  );

  let body;
  if (!user) {
    body = (
      <Link
        className="mt-4 block text-center text-sm font-bold underline"
        href={`/login?next=${encodeURIComponent(`/listings/${listing.id}`)}`}
      >
        Log in to propose a meetup
      </Link>
    );
  } else if (sent || existing) {
    body = (
      <div className="mt-4">
        <Alert tone={sent ? "success" : "info"}>
          {sent
            ? `Sent! ${listing.owner_display_name} can accept or suggest changes.`
            : `You have an open proposal with ${listing.owner_display_name}.`}{" "}
          <Link className="font-bold underline" href="/meetings">
            View in Meetings
          </Link>
        </Alert>
      </div>
    );
  } else if (!open) {
    body = (
      <Button
        className="mt-4 w-full"
        onClick={() => setOpen(true)}
        variant="secondary"
      >
        Propose a meetup
      </Button>
    );
  } else {
    body = (
      <div className="mt-4">
        <MeetupTermsForm
          initial={{
            location: listing.mrt_station ? `${listing.mrt_station} MRT` : "",
            price: listing.price_day,
          }}
          onCancel={() => setOpen(false)}
          onSubmit={async (terms) => {
            await apiPost<Meetup>("/meetups", {
              listing_id: listing.id,
              ...terms,
              message: terms.message || null,
            });
            setSent(true);
            setOpen(false);
            meetups.reload();
          }}
          submitLabel="Send proposal"
        />
      </div>
    );
  }

  return (
    <Card className="mt-4">
      <strong className="text-lg">Meet the lender</strong>
      <p className="mt-1 text-sm leading-6 text-muted">
        Suggest a time, place and price. {listing.owner_display_name} can accept
        or counter, and once you both agree it appears in your Meetings.
      </p>
      {body}
    </Card>
  );
}

function StatusBadge({ meetup }: { meetup: Meetup }) {
  const other =
    meetup.viewer_role === "borrower"
      ? meetup.lender_display_name
      : meetup.borrower_display_name;
  switch (meetup.status) {
    case "pending":
      return awaitingMe(meetup) ? (
        <Badge tone="warning">Waiting for you</Badge>
      ) : (
        <Badge tone="info">Waiting for {other.split(" ")[0]}</Badge>
      );
    case "accepted":
      return isUpcoming(meetup) ? (
        <Badge tone="success">Scheduled</Badge>
      ) : (
        <Badge>Past</Badge>
      );
    case "declined":
      return <Badge tone="danger">Declined</Badge>;
    default:
      return <Badge>Cancelled</Badge>;
  }
}

const verbs: Record<MeetupEvent["kind"], string> = {
  propose: "proposed",
  counter: "suggested changes",
  accept: "accepted",
  decline: "declined",
  cancel: "cancelled",
};

function Conversation({
  meetup,
  viewerId,
}: {
  meetup: Meetup;
  viewerId?: string;
}) {
  return (
    <details className="mt-4 border-t border-line pt-3 text-sm">
      <summary className="cursor-pointer font-bold">
        Conversation ({meetup.events.length})
      </summary>
      <ol className="mt-3 space-y-3">
        {meetup.events.map((event) => (
          <li className="leading-6" key={event.id}>
            <span className="font-bold">
              {event.author_id === viewerId ? "You" : event.author_display_name}
            </span>{" "}
            {verbs[event.kind]}
            <span className="text-muted">
              {" "}
              · {formatMeetingTime(event.created_at)}
            </span>
            {event.meet_at && (
              <p className="text-muted">
                {formatMeetingTime(event.meet_at)} · {event.location} ·{" "}
                {money(event.price)}
              </p>
            )}
            {event.message && (
              <p className="mt-1 rounded-lg bg-sand px-3 py-2">
                {event.message}
              </p>
            )}
          </li>
        ))}
      </ol>
    </details>
  );
}

export function MeetupCard({
  meetup,
  onChange,
}: {
  meetup: Meetup;
  onChange: () => void;
}) {
  const { user } = useSession();
  const [countering, setCountering] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState<string>();
  const actions = meetup.available_actions;
  const other =
    meetup.viewer_role === "borrower"
      ? { id: meetup.lender_id, name: meetup.lender_display_name }
      : { id: meetup.borrower_id, name: meetup.borrower_display_name };
  const latest = meetup.events.at(-1);

  async function act(action: "accept" | "decline" | "cancel") {
    setBusy(action);
    setError(undefined);
    try {
      await apiPost<Meetup>(`/meetups/${meetup.id}/${action}`, {
        message: note.trim() || null,
      });
      setNote("");
      onChange();
    } catch (caught) {
      setError(errorText(caught, "That didn't work. Try again."));
      onChange();
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            className="text-lg font-extrabold underline-offset-2 hover:underline"
            href={`/listings/${meetup.listing_id}`}
          >
            {meetup.listing_title}
          </Link>
          <p className="text-sm text-muted">
            {meetup.viewer_role === "borrower"
              ? "Borrowing from "
              : "Lending to "}
            <Link className="font-bold underline" href={`/users/${other.id}`}>
              {other.name}
            </Link>
          </p>
        </div>
        <StatusBadge meetup={meetup} />
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <Term label="When" value={formatMeetingTime(meetup.meet_at)} />
        <Term label="Where" value={meetup.location} />
        <Term label="Price" value={money(meetup.price)} />
      </dl>

      {latest?.message &&
        latest.author_id !== user?.user_id &&
        meetup.status === "pending" && (
          <p className="mt-3 rounded-lg bg-sand px-3 py-2 text-sm">
            <span className="font-bold">{latest.author_display_name}:</span>{" "}
            {latest.message}
          </p>
        )}

      {error && (
        <div className="mt-4">
          <Alert>{error}</Alert>
        </div>
      )}

      {countering ? (
        <div className="mt-5 border-t border-line pt-5">
          <p className="mb-3 font-extrabold">Suggest different terms</p>
          <MeetupTermsForm
            initial={{
              meet_at: meetup.meet_at,
              location: meetup.location,
              price: meetup.price,
            }}
            onCancel={() => setCountering(false)}
            onSubmit={async (terms) => {
              await apiPost<Meetup>(`/meetups/${meetup.id}/counter`, {
                ...terms,
                message: terms.message || null,
              });
              setCountering(false);
              onChange();
            }}
            submitLabel="Send counter-offer"
          />
        </div>
      ) : (
        actions.length > 0 && (
          <div className="mt-5 space-y-3">
            {actions.some((a) => a !== "counter") && (
              <Input
                aria-label="Add a note (optional)"
                maxLength={500}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add a note (optional)"
                value={note}
              />
            )}
            <div className="flex flex-wrap gap-3">
              {actions.includes("accept") && (
                <Button
                  busy={busy === "accept"}
                  disabled={!!busy}
                  onClick={() => act("accept")}
                >
                  Accept
                </Button>
              )}
              {actions.includes("counter") && (
                <Button
                  disabled={!!busy}
                  onClick={() => setCountering(true)}
                  variant="secondary"
                >
                  Counter-propose
                </Button>
              )}
              {actions.includes("decline") && (
                <Button
                  busy={busy === "decline"}
                  disabled={!!busy}
                  onClick={() => act("decline")}
                  variant="ghost"
                >
                  Decline
                </Button>
              )}
              {actions.includes("cancel") && (
                <Button
                  busy={busy === "cancel"}
                  disabled={!!busy}
                  onClick={() => act("cancel")}
                  variant="secondary"
                >
                  {meetup.status === "pending"
                    ? "Withdraw offer"
                    : "Cancel meeting"}
                </Button>
              )}
            </div>
          </div>
        )
      )}

      <Conversation meetup={meetup} viewerId={user?.user_id} />
    </Card>
  );
}

function Term({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-forest-soft p-3">
      <dt className="text-xs font-bold text-muted">{label}</dt>
      <dd className="mt-1 font-extrabold">{value}</dd>
    </div>
  );
}

/** Dashboard block: open proposals for one role (yours to answer first) and upcoming meetings. */
export function MeetupSection({
  role,
  title,
}: {
  role: "borrower" | "lender";
  title: string;
}) {
  const { meetups } = useAccountData();
  if (meetups.loading && !meetups.data) return <Spinner />;
  if (meetups.error) return <Alert>{meetups.error.message}</Alert>;
  const mine = meetups.data?.filter((m) => m.viewer_role === role) ?? [];
  const open = mine
    .filter((m) => m.status === "pending")
    .sort((a, b) => Number(awaitingMe(b)) - Number(awaitingMe(a)));
  const upcoming = mine
    .filter((m) => m.status === "accepted" && isUpcoming(m))
    .sort((a, b) => a.meet_at.localeCompare(b.meet_at));
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-extrabold">{title}</h2>
        <Link className="text-sm font-bold underline" href="/meetings">
          All meetings
        </Link>
      </div>
      {open.length === 0 && upcoming.length === 0 && (
        <EmptyState
          title={
            role === "lender"
              ? "No meetup requests yet"
              : "No meetup proposals yet"
          }
        >
          {role === "lender"
            ? "When a borrower proposes a time, place and price, it shows up here."
            : "Propose a meetup from any listing to agree on a time, place and price."}
        </EmptyState>
      )}
      {open.map((meetup) => (
        <MeetupCard key={meetup.id} meetup={meetup} onChange={meetups.reload} />
      ))}
      {upcoming.length > 0 && (
        <p className="pt-2 text-sm text-muted">
          {upcoming.length} upcoming meeting{upcoming.length === 1 ? "" : "s"},
          next on{" "}
          <Link className="font-bold underline" href="/meetings">
            {formatMeetingTime(upcoming[0].meet_at)}
          </Link>
          .
        </p>
      )}
    </section>
  );
}
