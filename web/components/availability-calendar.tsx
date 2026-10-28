"use client";

import { useEffect, useState } from "react";
import { type Schemas, withQuery } from "@/lib/api-client";
import { isoDate } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { Alert, Button, Card, Spinner } from "./ui";

export function AvailabilityCalendar({
  id,
  version,
}: {
  id: string;
  version: number;
}) {
  const [month, setMonth] = useState(isoDate(new Date()).slice(0, 7) + "-01");
  const [year, monthNumber] = month.split("-").map(Number);
  const first = new Date(year, monthNumber - 1, 1);
  const last = new Date(year, monthNumber, 0);
  const availability = useApi<Schemas["AvailabilityResponse"]>(
    withQuery(`/listings/${id}/availability`, {
      from: month,
      to: isoDate(last),
    }),
  );
  const reload = availability.reload;
  useEffect(() => {
    reload();
  }, [version, reload]);
  const offset = (first.getDay() + 6) % 7;
  const slots = Math.ceil((offset + last.getDate()) / 7) * 7;
  const cells = Array.from({ length: slots }, (_, index) => {
    const day = index - offset + 1;
    if (day < 1 || day > last.getDate()) return null;
    const date = isoDate(new Date(year, monthNumber - 1, day));
    const inside = (window: Schemas["DateWindow"]) =>
      window.start_date <= date && date <= window.end_date;
    const state = availability.data?.booked.some(inside)
      ? "Booked"
      : availability.data?.windows.some(inside)
        ? "Open"
        : "Closed";
    return { day, date, state };
  });
  function move(direction: number) {
    setMonth(isoDate(new Date(year, monthNumber - 1 + direction, 1)));
  }
  return (
    <Card className="mb-6">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="text-xl font-bold">Availability calendar</h2>
        <div className="flex gap-1">
          <Button
            type="button"
            variant="ghost"
            aria-label="Previous month"
            onClick={() => move(-1)}
          >
            ←
          </Button>
          <Button
            type="button"
            variant="ghost"
            aria-label="Next month"
            onClick={() => move(1)}
          >
            →
          </Button>
        </div>
      </div>
      {availability.loading && <Spinner label="Loading calendar…" />}
      {availability.error && (
        <Alert>
          {availability.error.message}
          <Button type="button" onClick={reload} variant="secondary">
            Try again
          </Button>
        </Alert>
      )}
      {availability.data && !availability.loading && (
        <table className="w-full table-fixed border-separate border-spacing-1 text-center text-xs">
          <caption className="mb-3 text-base font-bold">
            {first.toLocaleDateString("en-SG", {
              month: "long",
              year: "numeric",
            })}
          </caption>
          <thead>
            <tr>
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
                <th scope="col" key={day}>
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: slots / 7 }, (_, row) => (
              <tr key={row}>
                {cells.slice(row * 7, row * 7 + 7).map((cell, column) => (
                  <td
                    key={column}
                    aria-label={
                      cell ? `${cell.date}: ${cell.state}` : undefined
                    }
                    className={`h-9 rounded-md ${!cell ? "" : cell.state === "Booked" ? "bg-orange text-ink font-bold" : cell.state === "Open" ? "bg-sage text-forest" : "bg-sand text-muted"}`}
                  >
                    {cell?.day}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="mt-3 flex flex-wrap gap-4 text-xs">
        <span>
          <span
            aria-hidden="true"
            className="mr-1 inline-block size-3 rounded bg-sage"
          />
          Open
        </span>
        <span>
          <span
            aria-hidden="true"
            className="mr-1 inline-block size-3 rounded bg-orange"
          />
          Booked
        </span>
        <span>
          <span
            aria-hidden="true"
            className="mr-1 inline-block size-3 rounded bg-sand"
          />
          Closed
        </span>
      </p>
      <p className="mt-3 text-xs leading-5 text-muted">
        Change open dates below. Booked dates stay reserved even when you edit
        your windows.
      </p>
    </Card>
  );
}
