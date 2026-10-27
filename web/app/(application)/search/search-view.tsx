"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { ListingCard } from "@/components/listing-card";
import {
  Alert,
  Button,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
} from "@/components/ui";
import { type Schemas, withQuery } from "@/lib/api-client";
import { CATEGORIES } from "@/lib/catalogue";
import { isoDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";

const PAGE = 20;
const FILTERS = [
  "q",
  "category",
  "mrt",
  "min_price",
  "max_price",
  "from",
  "to",
] as const;
type Filters = Record<(typeof FILTERS)[number], string>;

export function SearchView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const applied = Object.fromEntries(
    FILTERS.map((key) => [key, params.get(key) ?? ""]),
  ) as Filters;
  const [draft, setDraft] = useState<Filters>(applied);
  const requestedPage = Number(params.get("page") ?? 1);
  const page =
    Number.isSafeInteger(requestedPage) && requestedPage > 0
      ? requestedPage
      : 1;
  const query = withQuery("/listings", {
    ...applied,
    limit: PAGE,
    offset: (page - 1) * PAGE,
  });
  const results = useApi<Schemas["Listing"][]>(query);
  const stations = useApi<Schemas["MrtStation"][]>("/listings/mrt-stations");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const paramsKey = params.toString();

  useEffect(() => {
    setDraft(
      Object.fromEntries(
        FILTERS.map((key) => [key, params.get(key) ?? ""]),
      ) as Filters,
    );
  }, [paramsKey]);

  const listings = results.loading || results.error ? [] : (results.data ?? []);
  const dateError =
    draft.from && draft.to && draft.to < draft.from
      ? "End date is before start date."
      : undefined;

  function apply(event?: FormEvent, next: Filters = draft) {
    event?.preventDefault();
    if (next.from && next.to && next.to < next.from) return;
    setFiltersOpen(false);
    router.push(withQuery(pathname, next));
  }

  const set = (key: keyof Filters) => (e: { target: { value: string } }) =>
    setDraft((current) => ({ ...current, [key]: e.target.value }));
  const activeCount = FILTERS.filter(
    (key) => key !== "q" && applied[key],
  ).length;

  return (
    <>
      <PageHeader
        eyebrow="Explore"
        title="Find it nearby"
        description="Rent from people around you. Pick dates to see only what is free."
      />
      <form className="mb-5 flex gap-2" onSubmit={apply} role="search">
        <Input
          aria-label="Search rentals"
          onChange={set("q")}
          placeholder="Tent, drill, camera…"
          type="search"
          value={draft.q}
        />
        <Button type="submit">Search</Button>
      </form>
      <div className="grid gap-5 lg:grid-cols-[250px_1fr]">
        <button
          aria-expanded={filtersOpen}
          className="flex items-center justify-between rounded-xl border border-line bg-white px-4 py-3 text-sm font-extrabold lg:hidden"
          onClick={() => setFiltersOpen((open) => !open)}
          type="button"
        >
          <span>Search & filters{activeCount > 0 && ` (${activeCount})`}</span>
          <span aria-hidden>{filtersOpen ? "▲" : "▼"}</span>
        </button>
        <form
          className={`${filtersOpen ? "block" : "hidden"} h-fit space-y-5 rounded-card border border-line bg-white p-5 lg:sticky lg:top-28 lg:block`}
          onSubmit={apply}
        >
          <Field label="Category">
            <Select onChange={set("category")} value={draft.category}>
              <option value="">All categories</option>
              {CATEGORIES.map((category) => (
                <option key={category.name} value={category.name}>
                  {category.icon} {category.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Near MRT">
            <Select onChange={set("mrt")} value={draft.mrt}>
              <option value="">All Singapore</option>
              {stations.data?.map((station) => (
                <option key={station.name} value={station.name}>
                  {station.name}
                </option>
              ))}
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min / day">
              <Input
                inputMode="decimal"
                min={0}
                onChange={set("min_price")}
                placeholder="S$"
                type="number"
                value={draft.min_price}
              />
            </Field>
            <Field label="Max / day">
              <Input
                inputMode="decimal"
                min={0}
                onChange={set("max_price")}
                placeholder="S$"
                type="number"
                value={draft.max_price}
              />
            </Field>
          </div>
          <Field label="Free from">
            <Input
              min={isoDate(new Date())}
              onChange={set("from")}
              type="date"
              value={draft.from}
            />
          </Field>
          <Field label="Until" error={dateError}>
            <Input
              min={draft.from || isoDate(new Date())}
              onChange={set("to")}
              type="date"
              value={draft.to}
            />
          </Field>
          <Button className="w-full" type="submit">
            Show results
          </Button>
          {(activeCount > 0 || applied.q) && (
            <button
              className="w-full text-sm font-bold text-muted underline"
              onClick={() =>
                apply(
                  undefined,
                  Object.fromEntries(
                    FILTERS.map((key) => [key, ""]),
                  ) as Filters,
                )
              }
              type="button"
            >
              Clear all filters
            </button>
          )}
        </form>

        <section aria-live="polite">
          {results.loading && <Spinner label="Finding rentals…" />}
          {results.error && (
            <Alert title="Search failed">
              {results.error.message}{" "}
              <Button onClick={results.reload} variant="secondary">
                Try again
              </Button>
            </Alert>
          )}
          {results.data && listings.length === 0 && (
            <EmptyState title="Nothing matches yet">
              Try fewer filters, other dates or a nearby MRT station.{" "}
              {page > 1 && (
                <Button
                  onClick={() => router.push(withQuery(pathname, applied))}
                  variant="secondary"
                >
                  First page
                </Button>
              )}
            </EmptyState>
          )}
          {listings.length > 0 && (
            <>
              <p className="mb-4 text-sm text-muted">
                {listings.length} item{listings.length === 1 ? "" : "s"}
                {applied.from && " free for your dates"}
              </p>
              <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-3">
                {listings.map((listing) => (
                  <ListingCard
                    href={withQuery(`/listings/${listing.id}`, {
                      from: applied.from,
                      to: applied.to,
                      back: withQuery(pathname, {
                        ...applied,
                        page: page > 1 ? page : null,
                      }),
                    })}
                    key={listing.id}
                    listing={listing}
                  />
                ))}
              </div>
              <nav
                className="mt-8 flex items-center justify-center gap-4"
                aria-label="Search pages"
              >
                {page > 1 && (
                  <Button
                    variant="secondary"
                    onClick={() =>
                      router.push(
                        withQuery(pathname, { ...applied, page: page - 1 }),
                      )
                    }
                  >
                    Previous
                  </Button>
                )}
                <span className="text-sm text-muted">Page {page}</span>
                {listings.length === PAGE && (
                  <Button
                    variant="secondary"
                    onClick={() =>
                      router.push(
                        withQuery(pathname, { ...applied, page: page + 1 }),
                      )
                    }
                  >
                    Next
                  </Button>
                )}
              </nav>
            </>
          )}
        </section>
      </div>
    </>
  );
}
