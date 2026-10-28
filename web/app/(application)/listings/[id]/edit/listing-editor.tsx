"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ListingPhoto } from "@/components/listing-card";
import { useSession } from "@/components/session";
import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  Input,
  LinkButton,
  PageHeader,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { apiRequest, type Schemas, withQuery } from "@/lib/api-client";
import { CONDITIONS } from "@/lib/catalogue";
import { addDays, isoDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";

type Listing = Schemas["ListingDetail"];
type Window = Schemas["DateWindow"];

export function ListingEditor({ id }: { id: string }) {
  const listing = useApi<Listing>(`/listings/${id}`);
  const { user } = useSession();
  if (listing.loading) return <Spinner label="Loading your listing…" />;
  if (listing.error || !listing.data)
    return (
      <Alert>
        {listing.error?.message}
        <Button onClick={listing.reload} variant="secondary">
          Try again
        </Button>
      </Alert>
    );
  if (listing.data.owner_id !== user?.user_id)
    return (
      <Alert>
        This listing belongs to another lender.{" "}
        <Link href="/listings/manage" className="underline">
          Back to your listings
        </Link>
      </Alert>
    );
  return (
    <>
      <Link className="text-sm font-bold text-muted" href="/listings/manage">
        ← My listings
      </Link>
      <PageHeader title="Manage listing" />
      <div className="mb-6 flex items-center gap-4">
        <div className="w-24 shrink-0 overflow-hidden rounded-xl">
          <ListingPhoto listing={listing.data} />
        </div>
        <div>
          <h2 className="text-xl font-bold">{listing.data.title}</h2>
          <Badge
            tone={listing.data.status === "active" ? "success" : "warning"}
          >
            {listing.data.status}
          </Badge>
          <div className="mt-2">
            <Link className="text-sm underline" href={`/listings/${id}`}>
              View listing →
            </Link>
          </div>
        </div>
      </div>
      <DetailsForm listing={listing.data} onSave={listing.setData} />
      <AvailabilityEditor id={id} />
      <DeleteListing id={id} />
    </>
  );
}

function DeleteListing({ id }: { id: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function remove() {
    if (
      !window.confirm(
        "Delete this listing? It will be removed from search and can't be booked. Existing booking history is kept.",
      )
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest<Listing>(`/listings/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "archived" }),
      });
      router.push("/listings/manage");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Couldn't delete listing.",
      );
      setBusy(false);
    }
  }
  return (
    <section className="mt-6">
      <Card className="space-y-4">
        <h2 className="text-xl font-bold">Delete listing</h2>
        <p className="text-sm leading-6 text-muted">
          Removes the listing from search and frees up a listing slot. Listings
          with confirmed or active bookings can't be deleted.
        </p>
        {error && <Alert>{error}</Alert>}
        <Button busy={busy} type="button" variant="secondary" onClick={remove}>
          Delete listing
        </Button>
      </Card>
    </section>
  );
}

function DetailsForm({
  listing,
  onSave,
}: {
  listing: Listing;
  onSave: (listing: Listing) => void;
}) {
  const [form, setForm] = useState({
    title: listing.title,
    description: listing.description ?? "",
    condition: listing.condition,
    price_day: listing.price_day,
    price_week: listing.price_week ?? "",
    price_month: listing.price_month ?? "",
    deposit: listing.deposit,
    status: listing.status,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const set =
    (key: keyof typeof form) => (event: { target: { value: string } }) => {
      setSaved(false);
      setForm((current) => ({ ...current, [key]: event.target.value }));
    };
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await apiRequest<Listing>(`/listings/${listing.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...form,
          title: form.title.trim(),
          description: form.description.trim() || null,
          price_week: form.price_week || null,
          price_month: form.price_month || null,
        }),
      });
      onSave(updated);
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Couldn't save listing.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <Card className="space-y-5">
        <h2 className="text-xl font-bold">Details & pricing</h2>
        <Field label="Title">
          <Input
            required
            minLength={3}
            maxLength={120}
            value={form.title}
            onChange={set("title")}
          />
        </Field>
        <Field label="Description">
          <Textarea
            maxLength={2000}
            value={form.description}
            onChange={set("description")}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Condition">
            <Select value={form.condition} onChange={set("condition")}>
              {!CONDITIONS.some(
                (condition) => condition === form.condition,
              ) && <option>{form.condition}</option>}
              {CONDITIONS.map((condition) => (
                <option key={condition}>{condition}</option>
              ))}
            </Select>
          </Field>
          <Field label="Visibility">
            <Select value={form.status} onChange={set("status")}>
              <option value="active">Active — visible in search</option>
              <option value="paused">Paused — hidden from search</option>
              {listing.status === "archived" && (
                <option value="archived">Archived</option>
              )}
            </Select>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {(
            [
              ["price_day", "Per day (S$)"],
              ["price_week", "Per week (optional)"],
              ["price_month", "Per month (optional)"],
              ["deposit", "Deposit (S$)"],
            ] as const
          ).map(([key, label]) => (
            <Field key={key} label={label}>
              <Input
                required={key === "price_day" || key === "deposit"}
                type="number"
                inputMode="decimal"
                min={key === "deposit" ? 0 : 0.01}
                step="0.01"
                value={form[key]}
                onChange={set(key)}
              />
            </Field>
          ))}
        </div>
        {error && <Alert>{error}</Alert>}
        {saved && <Alert tone="success">Listing saved.</Alert>}
        <Button busy={busy} type="submit">
          Save listing
        </Button>
      </Card>
    </form>
  );
}

function AvailabilityEditor({ id }: { id: string }) {
  const today = isoDate(new Date());
  const availability = useApi<Schemas["AvailabilityResponse"]>(
    withQuery(`/listings/${id}/availability`, {
      from: today,
      to: addDays(today, 365),
    }),
  );
  return (
    <section className="mt-6">
      {availability.loading && <Spinner label="Loading open dates…" />}
      {availability.error && (
        <Alert>
          {availability.error.message}
          <Button onClick={availability.reload} variant="secondary">
            Try again
          </Button>
        </Alert>
      )}
      {availability.data && (
        <AvailabilityForm
          key={id}
          id={id}
          initial={availability.data.windows}
        />
      )}
    </section>
  );
}

function AvailabilityForm({ id, initial }: { id: string; initial: Window[] }) {
  const [windows, setWindows] = useState<Window[]>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  function change(index: number, key: keyof Window, value: string) {
    setSaved(false);
    setWindows((current) =>
      current.map((window, i) =>
        i === index ? { ...window, [key]: value } : window,
      ),
    );
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    if (
      !windows.length ||
      windows.some(
        (window) => !window.start_date || window.end_date < window.start_date,
      )
    ) {
      setError(
        "Each open window needs an end date on or after its start date.",
      );
      return;
    }
    setBusy(true);
    try {
      const updated = await apiRequest<Schemas["AvailabilityResponse"]>(
        `/listings/${id}/availability`,
        { method: "PUT", body: JSON.stringify({ windows }) },
      );
      setWindows(updated.windows);
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Couldn't save open dates.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <Card className="space-y-5">
        <h2 className="text-xl font-bold">Open dates</h2>
        <p className="text-sm leading-6 text-muted">
          People can book within these windows. Existing bookings stay in place
          when you change availability. Pause the listing to stop new bookings
          entirely.
        </p>
        {windows.map((window, index) => (
          <fieldset key={index} className="rounded-xl border border-line p-4">
            <legend className="px-1 text-sm font-bold">
              Window {index + 1}
            </legend>
            <div className="grid grid-cols-2 gap-3">
              <Field label="From">
                <Input
                  required
                  type="date"
                  value={window.start_date}
                  onChange={(event) =>
                    change(index, "start_date", event.target.value)
                  }
                />
              </Field>
              <Field label="Until">
                <Input
                  required
                  type="date"
                  min={window.start_date}
                  value={window.end_date}
                  onChange={(event) =>
                    change(index, "end_date", event.target.value)
                  }
                />
              </Field>
            </div>
            {windows.length > 1 && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setSaved(false);
                  setWindows((current) =>
                    current.filter((_, i) => i !== index),
                  );
                }}
              >
                Remove window {index + 1}
              </Button>
            )}
          </fieldset>
        ))}
        {windows.length < 20 && (
          <Button
            variant="secondary"
            type="button"
            onClick={() => {
              setSaved(false);
              const today = isoDate(new Date());
              setWindows((current) => [
                ...current,
                { start_date: today, end_date: addDays(today, 30) },
              ]);
            }}
          >
            + Add window
          </Button>
        )}
        {error && <Alert>{error}</Alert>}
        {saved && <Alert tone="success">Open dates saved.</Alert>}
        <div>
          <Button busy={busy} type="submit">
            Save open dates
          </Button>
        </div>
      </Card>
    </form>
  );
}
