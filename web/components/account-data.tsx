"use client";

import { createContext, useContext, useEffect, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { apiRequest, type Schemas } from "@/lib/api-client";
import { useApi, type ApiState } from "@/lib/use-api";
import { addDays, isoDate } from "@/lib/format";
import { useSession } from "./session";

type AccountData = {
  saved: ApiState<Schemas["Listing"][]>;
  rentals: ApiState<Schemas["Booking"][]>;
  meetups: ApiState<Schemas["Meetup"][]>;
  toggleSaved: (id: string, saved: boolean) => Promise<void>;
};
const AccountContext = createContext<AccountData | null>(null);

export function AccountDataProvider({ children }: { children: ReactNode }) {
  const { user } = useSession();
  return (
    <AccountDataState
      key={user?.user_id ?? "guest"}
      authenticated={user !== null}
    >
      {children}
    </AccountDataState>
  );
}

function AccountDataState({
  children,
  authenticated,
}: {
  children: ReactNode;
  authenticated: boolean;
}) {
  const saved = useApi<Schemas["Listing"][]>(
    authenticated ? "/saved-listings" : null,
  );
  const rentals = useApi<Schemas["Booking"][]>(
    authenticated ? "/bookings?role=all&limit=100" : null,
  );
  const meetups = useApi<Schemas["Meetup"][]>(
    authenticated ? "/meetups?limit=100" : null,
  );
  const pathname = usePathname();
  const reloadRentals = rentals.reload;
  const reloadSaved = saved.reload;
  const reloadMeetups = meetups.reload;
  useEffect(() => {
    if (authenticated) {
      reloadRentals();
      reloadMeetups();
    }
  }, [pathname, authenticated, reloadRentals, reloadMeetups]);
  useEffect(() => {
    if (!authenticated) return;
    const refresh = () => {
      reloadRentals();
      reloadSaved();
      reloadMeetups();
    };
    const timer = window.setInterval(refresh, 60_000);
    window.addEventListener("focus", refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [authenticated, reloadRentals, reloadSaved, reloadMeetups]);
  async function toggleSaved(id: string, isSaved: boolean) {
    await apiRequest(`/saved-listings/${id}`, {
      method: isSaved ? "DELETE" : "PUT",
    });
    saved.reload();
  }
  return (
    <AccountContext value={{ saved, rentals, meetups, toggleSaved }}>
      {children}
    </AccountContext>
  );
}

export function useAccountData(): AccountData {
  const context = useContext(AccountContext);
  if (!context) throw new Error("AccountDataProvider is required");
  return context;
}

/** Reminders are derived from booking dates/actions, rather than unread notifications. */
export function rentalReminder(
  booking: Schemas["Booking"],
  today: string,
): string | null {
  if (
    booking.state === "confirmed" &&
    booking.start_date <= addDays(today, 2)
  ) {
    return booking.start_date < today
      ? "Pickup overdue — check the booking"
      : booking.start_date === today
        ? "Pickup today"
        : "Pickup coming up";
  }
  if (
    booking.state === "handed_over" &&
    booking.end_date <= addDays(today, 2)
  ) {
    return booking.end_date < today
      ? "Return overdue — check the booking"
      : booking.end_date === today
        ? "Return due today"
        : "Return coming up";
  }
  if (
    booking.state === "returned" &&
    booking.available_actions.includes("settle")
  )
    return "Check the return and settle the deposit";
  return null;
}

export function useRentalReminders() {
  const { rentals } = useAccountData();
  const today = isoDate(new Date());
  return {
    ...rentals,
    reminders: (rentals.data ?? []).flatMap((booking) => {
      const label = rentalReminder(booking, today);
      return label ? [{ booking, label }] : [];
    }),
  };
}
