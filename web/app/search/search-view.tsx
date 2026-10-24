"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { ListingCard } from "@/components/listing-card";
import { Alert, Button, EmptyState, Field, Input, PageHeader, Select, Spinner } from "@/components/ui";
import { apiRequest, type Schemas, withQuery } from "@/lib/api-client";
import { CATEGORIES } from "@/lib/catalogue";
import { isoDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";

const PAGE = 20;
const FILTERS = ["q", "category", "mrt", "min_price", "max_price", "from", "to"] as const;
type Filters = Record<(typeof FILTERS)[number], string>;

export function SearchView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const applied = Object.fromEntries(FILTERS.map((key) => [key, params.get(key) ?? ""])) as Filters;
  const [draft, setDraft] = useState<Filters>(applied);
  const query = withQuery("/listings", { ...applied, limit: PAGE });
  const results = useApi<Schemas["Listing"][]>(query);
  const stations = useApi<Schemas["MrtStation"][]>("/listings/mrt-stations");
  const [more, setMore] = useState<Schemas["Listing"][]>([]);
  const [exhausted, setExhausted] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const paramsKey = params.toString();

  useEffect(() => {
    setDraft(Object.fromEntries(FILTERS.map((key) => [key, params.get(key) ?? ""])) as Filters);
    setMore([]);
    setExhausted(false);
  }, [paramsKey]);

  const listings = [...(results.data ?? []), ...more];
  const dateError = draft.from && draft.to && draft.to < draft.from ? "End date is before start date." : undefined;

  function apply(event?: FormEvent, next: Filters = draft) {
    event?.preventDefault();
    if (dateError) return;
    setFiltersOpen(false);
    router.push(withQuery(pathname, next));
  }

  async function loadMore() {
    setLoadingMore(true);
    try {
      const page = await apiRequest<Schemas["Listing"][]>(
        withQuery("/listings", { ...applied, limit: PAGE, offset: listings.length }),
      );
      setMore((current) => [...current, ...page]);
      setExhausted(page.length < PAGE);
    } finally {
      setLoadingMore(false);
    }
  }

  const set = (key: keyof Filters) => (e: { target: { value: string } }) =>
    setDraft((current) => ({ ...current, [key]: e.target.value }));
  const activeCount = FILTERS.filter((key) => key !== "q" && applied[key]).length;

  return (
    <>
      <PageHeader
        eyebrow="Explore"
        title="Find it nearby"
        description="Rent from people around you. Pick dates to see only what is free."
      />
      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        <button
          aria-expanded={filtersOpen}
          className="flex items-center justify-between rounded-xl border border-line bg-white px-4 py-3 text-sm font-extrabold lg:hidden"
          onClick={() => setFiltersOpen((open) => !open)}
          type="button"
        >
          <span>
            Search & filters{activeCount > 0 && ` (${activeCount})`}
          </span>
          <span aria-hidden>{filtersOpen ? "▲" : "▼"}</span>
        </button>
        <form
          className={`${filtersOpen ? "block" : "hidden"} h-fit space-y-5 rounded-card border border-line bg-white p-5 lg:sticky lg:top-28 lg:block`}
          onSubmit={apply}
        >
          <Field label="Search">
            <Input onChange={set("q")} placeholder="Tent, drill, camera…" type="search" value={draft.q} />
          </Field>
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
              <Input inputMode="decimal" min={0} onChange={set("min_price")} placeholder="S$" type="number" value={draft.min_price} />
            </Field>
            <Field label="Max / day">
              <Input inputMode="decimal" min={0} onChange={set("max_price")} placeholder="S$" type="number" value={draft.max_price} />
            </Field>
          </div>
          <Field label="Free from">
            <Input min={isoDate(new Date())} onChange={set("from")} type="date" value={draft.from} />
          </Field>
          <Field label="Until" error={dateError}>
            <Input min={draft.from || isoDate(new Date())} onChange={set("to")} type="date" value={draft.to} />
          </Field>
          <Button className="w-full" type="submit">
            Show results
          </Button>
          {(activeCount > 0 || applied.q) && (
            <button
              className="w-full text-sm font-bold text-muted underline"
              onClick={() => apply(undefined, Object.fromEntries(FILTERS.map((key) => [key, ""])) as Filters)}
              type="button"
            >
              Clear all filters
            </button>
          )}
        </form>

        <section aria-live="polite">
          {results.loading && <Spinner label="Finding rentals…" />}
          {results.error && <Alert title="Search failed">{results.error.message}</Alert>}
          {results.data && listings.length === 0 && (
            <EmptyState title="Nothing matches yet">Try fewer filters, other dates or a nearby MRT station.</EmptyState>
          )}
          {listings.length > 0 && (
            <>
              <p className="mb-4 text-sm text-muted">
                {listings.length} item{listings.length === 1 ? "" : "s"}
                {applied.from && " free for your dates"}
              </p>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {listings.map((listing) => (
                  <ListingCard
                    href={withQuery(`/listings/${listing.id}`, { from: applied.from, to: applied.to })}
                    key={listing.id}
                    listing={listing}
                  />
                ))}
              </div>
              {!exhausted && (results.data?.length ?? 0) === PAGE && (
                <div className="mt-8 text-center">
                  <Button busy={loadingMore} onClick={loadMore} variant="secondary">
                    Load more
                  </Button>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}
