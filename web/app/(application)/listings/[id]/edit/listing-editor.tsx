"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ConfirmAction } from "@/components/confirm-action";
import { AvailabilityCalendar } from "@/components/availability-calendar";
import { ListingPhotosEditor } from "@/components/listing-photos-editor";
import { ListingPhoto } from "@/components/listing-card";
import { useSession } from "@/components/session";
import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { apiRequest, type Schemas, withQuery } from "@/lib/api-client";
import { CATEGORIES, CONDITIONS } from "@/lib/catalogue";
import { addDays, isoDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";

type Listing = Schemas["ListingDetail"];
type Window = Schemas["DateWindow"];

export function ListingEditor({ id }: { id: string }) {
  const listing = useApi<Listing>(`/listings/${id}/manage`);
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
          {listing.data.status !== "archived" && (
            <div className="mt-2">
              <Link className="text-sm underline" href={`/listings/${id}`}>
                View listing →
              </Link>
            </div>
          )}
        </div>
      </div>
      <DetailsForm listing={listing.data} onSave={listing.setData} />
      <ListingPhotosEditor listing={listing.data} onSave={listing.setData} />
      <AvailabilityEditor id={id} />
      {listing.data.status !== "archived" && <DeleteListing id={id} />}
    </>
  );
}

function DeleteListing({ id }: { id: string }) {
  const router = useRouter();
  async function remove() {
    await apiRequest<Listing>(`/listings/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "archived" }),
    });
    router.push("/listings/manage");
  }
  return (
    <section className="mt-6">
      <Card className="space-y-4">
        <h2 className="text-xl font-bold">Delete listing</h2>
        <p className="text-sm leading-6 text-muted">
          Removes the listing from search and frees up a listing slot. Listings
          with confirmed or active bookings can't be deleted.
        </p>
        <ConfirmAction
          title="Delete this listing?"
          description="The listing will be archived and removed from search. Existing booking history is kept. You can restore it from My listings."
          trigger="Delete listing"
          confirmLabel="Delete listing"
          variant="danger"
          onConfirm={remove}
          disabled={false}
        />
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
    category: listing.category,
    mrt_station: listing.mrt_station ?? "",
    postal_code: "",
    price_day: listing.price_day,
    price_week: listing.price_week ?? "",
    price_month: listing.price_month ?? "",
    deposit: listing.deposit,
    status: listing.status,
  });
  const stations = useApi<Schemas["MrtStation"][]>("/listings/mrt-stations");
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
          postal_code: form.postal_code || undefined,
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
        <Field label="Category">
          <Select value={form.category} onChange={set("category")}>
            {!CATEGORIES.some(
              (category) => category.name === form.category,
            ) && <option>{form.category}</option>}
            {CATEGORIES.map((category) => (
              <option key={category.name} value={category.name}>
                {category.name}
              </option>
            ))}
          </Select>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Postal code"
            hint="Optional; used to find your nearest MRT, then discarded."
          >
            <Input
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              value={form.postal_code}
              onChange={set("postal_code")}
            />
          </Field>
          <Field label="Nearest MRT">
            <Select
              required={!form.postal_code}
              value={form.mrt_station}
              onChange={set("mrt_station")}
            >
              <option value="">Choose a station</option>
              {stations.data?.map((station) => (
                <option key={station.name}>{station.name}</option>
              ))}
            </Select>
          </Field>
        </div>
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
          <Field
            label="Visibility"
            hint="Archiving is reversible and preserves existing bookings."
          >
            <Select value={form.status} onChange={set("status")}>
              <option value="active">Active — visible in search</option>
              <option value="paused">Paused — hidden from search</option>
              <option value="archived">Archived — frees a listing slot</option>
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
  const [version, setVersion] = useState(0);
  const today = isoDate(new Date());
  const availability = useApi<Schemas["AvailabilityResponse"]>(
    withQuery(`/listings/${id}/availability`, {
      from: today,
      to: addDays(today, 365),
    }),
  );
  return (
    <section className="mt-6">
      <AvailabilityCalendar id={id} version={version} />
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
          onSaved={() => setVersion((value) => value + 1)}
        />
      )}
    </section>
  );
}

function AvailabilityForm({
  id,
  initial,
  onSaved,
}: {
  id: string;
  initial: Window[];
  onSaved: () => void;
}) {
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
      onSaved();
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
