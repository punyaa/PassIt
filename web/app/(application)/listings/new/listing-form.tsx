"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { PhotoPicker } from "@/components/photo-picker";
import {
  Alert,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError, apiPost, type Schemas } from "@/lib/api-client";
import { CATEGORIES, CONDITIONS } from "@/lib/catalogue";
import { addDays, isoDate, money } from "@/lib/format";
import { uploadMedia } from "@/lib/uploads";
import { useApi } from "@/lib/use-api";

type Form = {
  title: string;
  description: string;
  category: string;
  condition: string;
  postal_code: string;
  mrt_station: string;
  price_day: string;
  price_week: string;
  price_month: string;
  deposit: string;
  available_from: string;
  available_to: string;
};

const today = isoDate(new Date());
const initial: Form = {
  title: "",
  description: "",
  category: "",
  condition: "Good",
  postal_code: "",
  mrt_station: "",
  price_day: "",
  price_week: "",
  price_month: "",
  deposit: "",
  available_from: today,
  available_to: addDays(today, 365),
};

function validate(form: Form): Partial<Record<keyof Form, string>> {
  const errors: Partial<Record<keyof Form, string>> = {};
  const day = Number(form.price_day);
  if (form.title.trim().length < 3) errors.title = "At least 3 characters.";
  if (!form.category) errors.category = "Choose a category.";
  if (form.postal_code && !/^\d{6}$/.test(form.postal_code))
    errors.postal_code = "Six digits.";
  if (!form.postal_code && !form.mrt_station)
    errors.mrt_station = "Add a postal code or choose a station.";
  if (!(day > 0)) errors.price_day = "Enter a daily price.";
  if (form.price_week && Number(form.price_week) >= day * 7)
    errors.price_week = "Should be below 7 × daily.";
  if (
    form.price_month &&
    form.price_week &&
    Number(form.price_month) >= Number(form.price_week) * 4
  ) {
    errors.price_month = "Should be below 4 × weekly.";
  }
  if (form.deposit === "" || Number(form.deposit) < 0)
    errors.deposit = "Enter a deposit (0 is fine).";
  if (form.available_to < form.available_from)
    errors.available_to = "Ends before it starts.";
  return errors;
}

export function ListingForm() {
  const router = useRouter();
  const stations = useApi<Schemas["MrtStation"][]>("/listings/mrt-stations");
  const [form, setForm] = useState<Form>(initial);
  const [photos, setPhotos] = useState<File[]>([]);
  const [touched, setTouched] = useState(false);
  const [progress, setProgress] = useState<string>();
  const [error, setError] = useState<{ message: string; limit?: boolean }>();
  const [suggestion, setSuggestion] = useState<Schemas["PriceSuggestion"]>();
  const [suggesting, setSuggesting] = useState(false);
  const errors = touched ? validate(form) : {};
  const set = (key: keyof Form) => (e: { target: { value: string } }) =>
    setForm((current) => ({ ...current, [key]: e.target.value }));

  async function suggest() {
    setSuggesting(true);
    try {
      const result = await apiPost<Schemas["PriceSuggestion"]>(
        "/listings/price-suggestion",
        {
          title: form.title,
          category: form.category,
          condition: form.condition,
        },
      );
      setSuggestion(result);
      setForm((current) => ({
        ...current,
        price_day: result.day.recommended,
        price_week: result.week.recommended,
        price_month: result.month.recommended,
      }));
    } catch (caught) {
      setError({
        message:
          caught instanceof Error ? caught.message : "No suggestion right now.",
      });
    } finally {
      setSuggesting(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (Object.keys(validate(form)).length) return;
    setError(undefined);
    try {
      const photoKeys: string[] = [];
      for (const [index, file] of photos.entries()) {
        setProgress(`Uploading photo ${index + 1} of ${photos.length}…`);
        photoKeys.push(await uploadMedia(file, "listing"));
      }
      setProgress("Publishing your listing…");
      const listing = await apiPost<Schemas["ListingDetail"]>("/listings", {
        title: form.title.trim(),
        description: form.description.trim() || null,
        category: form.category,
        condition: form.condition,
        price_day: form.price_day,
        price_week: form.price_week || null,
        price_month: form.price_month || null,
        deposit: form.deposit,
        postal_code: form.postal_code || null,
        mrt_station: form.mrt_station || null,
        photo_keys: photoKeys,
        availability: [
          { start_date: form.available_from, end_date: form.available_to },
        ],
      });
      router.push(`/listings/${listing.id}`);
    } catch (caught) {
      setProgress(undefined);
      const limit = caught instanceof ApiError && caught.status === 403;
      setError({
        message:
          caught instanceof Error ? caught.message : "Could not publish.",
        limit,
      });
    }
  }

  const canSuggest = form.title.trim().length >= 3 && form.category;

  return (
    <>
      <PageHeader
        eyebrow="Earn from your items"
        title="List an item"
        description="Free accounts can list up to three items. Your exact address is never shown; borrowers see the nearest MRT station."
      />
      <form className="space-y-6" noValidate onSubmit={submit}>
        <Card className="space-y-5">
          <h2 className="text-xl font-extrabold">What are you lending?</h2>
          <Field label="Title" error={errors.title}>
            <Input
              maxLength={120}
              onChange={set("title")}
              placeholder="e.g. 4-person camping tent"
              value={form.title}
            />
          </Field>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Category" error={errors.category}>
              <Select onChange={set("category")} value={form.category}>
                <option value="">Choose…</option>
                {CATEGORIES.map((category) => (
                  <option key={category.name} value={category.name}>
                    {category.icon} {category.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Condition">
              <Select onChange={set("condition")} value={form.condition}>
                {CONDITIONS.map((condition) => (
                  <option key={condition}>{condition}</option>
                ))}
              </Select>
            </Field>
          </div>
          <Field
            label="Description"
            hint="What's included, any quirks, pickup notes."
          >
            <Textarea
              maxLength={2000}
              onChange={set("description")}
              value={form.description}
            />
          </Field>
          <Field
            label="Photos"
            hint="Clear photos get more bookings. They also back up the item's condition."
          >
            <PhotoPicker files={photos} onChange={setPhotos} />
          </Field>
        </Card>

        <Card className="space-y-5">
          <h2 className="text-xl font-extrabold">Where is it?</h2>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field
              label="Postal code"
              hint="Used once to find your nearest MRT. Never stored."
              error={errors.postal_code}
            >
              <Input
                inputMode="numeric"
                maxLength={6}
                onChange={set("postal_code")}
                placeholder="119077"
                value={form.postal_code}
              />
            </Field>
            <Field label="…or nearest MRT" error={errors.mrt_station}>
              <Select onChange={set("mrt_station")} value={form.mrt_station}>
                <option value="">Choose a station</option>
                {stations.data?.map((station) => (
                  <option key={station.name} value={station.name}>
                    {station.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
        </Card>

        <Card className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-extrabold">Pricing</h2>
            <Button
              busy={suggesting}
              disabled={!canSuggest}
              onClick={suggest}
              type="button"
              variant="secondary"
            >
              ✨ Suggest prices
            </Button>
          </div>
          {!canSuggest && (
            <p className="-mt-2 text-xs text-muted">
              Add a title and category to get a suggestion.
            </p>
          )}
          {suggestion && (
            <Alert tone="info">
              Suggested from{" "}
              {suggestion.source === "heuristic"
                ? "similar listings"
                : "our pricing model"}
              : day {money(suggestion.day.min)}–{money(suggestion.day.max)},
              week {money(suggestion.week.min)}–{money(suggestion.week.max)}.
              Adjust as you like.
            </Alert>
          )}
          <div className="grid gap-5 sm:grid-cols-3">
            <Field label="Per day (S$)" error={errors.price_day}>
              <Input
                inputMode="decimal"
                min={0}
                onChange={set("price_day")}
                step="0.5"
                type="number"
                value={form.price_day}
              />
            </Field>
            <Field label="Per week (optional)" error={errors.price_week}>
              <Input
                inputMode="decimal"
                min={0}
                onChange={set("price_week")}
                step="0.5"
                type="number"
                value={form.price_week}
              />
            </Field>
            <Field label="Per month (optional)" error={errors.price_month}>
              <Input
                inputMode="decimal"
                min={0}
                onChange={set("price_month")}
                step="0.5"
                type="number"
                value={form.price_month}
              />
            </Field>
          </div>
          <Field
            label="Refundable deposit (S$)"
            hint="Covers damage. Returned in full when the item comes back fine."
            error={errors.deposit}
          >
            <Input
              inputMode="decimal"
              min={0}
              onChange={set("deposit")}
              step="1"
              type="number"
              value={form.deposit}
            />
          </Field>
        </Card>

        <Card className="space-y-5">
          <h2 className="text-xl font-extrabold">When can people borrow it?</h2>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Available from">
              <Input
                min={today}
                onChange={set("available_from")}
                type="date"
                value={form.available_from}
              />
            </Field>
            <Field label="Available until" error={errors.available_to}>
              <Input
                min={form.available_from}
                onChange={set("available_to")}
                type="date"
                value={form.available_to}
              />
            </Field>
          </div>
        </Card>

        {error && (
          <Alert
            title={error.limit ? "Listing limit reached" : "Couldn't publish"}
          >
            {error.message}{" "}
            {error.limit && (
              <Link className="font-bold underline" href="/listings/manage">
                Manage your listings
              </Link>
            )}
          </Alert>
        )}
        {touched && Object.keys(errors).length > 0 && (
          <Alert>Fix the highlighted fields to continue.</Alert>
        )}
        <div className="flex items-center justify-end gap-4">
          {progress && <span className="text-sm text-muted">{progress}</span>}
          <Button busy={Boolean(progress)} type="submit" variant="accent">
            Publish listing
          </Button>
        </div>
      </form>
    </>
  );
}
