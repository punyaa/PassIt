const amount = new Intl.NumberFormat("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** SGD with an explicit "S$" prefix, as Singapore listings are usually written. */
export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return `${number < 0 ? "−" : ""}S$${amount.format(Math.abs(number))}`;
}

const day = new Intl.DateTimeFormat("en-SG", { day: "numeric", month: "short", year: "numeric" });
const dateTime = new Intl.DateTimeFormat("en-SG", {
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
});

/** Format an ISO date (YYYY-MM-DD) without timezone shifts. */
export function formatDate(iso: string): string {
  const [year, month, date] = iso.split("-").map(Number);
  return day.format(new Date(year, month - 1, date));
}

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : "—";
}

export function dateRange(start: string, end: string): string {
  return start === end ? formatDate(start) : `${formatDate(start)} – ${formatDate(end)}`;
}

/** Local calendar date as YYYY-MM-DD. */
export function isoDate(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function addDays(iso: string, days: number): string {
  const [year, month, date] = iso.split("-").map(Number);
  return isoDate(new Date(year, month - 1, date + days));
}

export function inclusiveDays(start: string, end: string): number {
  const toTime = (iso: string) => {
    const [year, month, date] = iso.split("-").map(Number);
    return Date.UTC(year, month - 1, date);
  };
  return Math.round((toTime(end) - toTime(start)) / 86_400_000) + 1;
}

export function timeUntil(iso: string, now: number): string {
  const ms = new Date(iso).getTime() - now;
  if (ms <= 0) return "any moment now";
  const minutes = Math.floor(ms / 60_000);
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  return `${Math.max(minutes, 1)}m`;
}
