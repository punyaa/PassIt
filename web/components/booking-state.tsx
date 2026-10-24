import type { Schemas } from "@/lib/api-client";

import { Badge } from "./ui";

type State = Schemas["Booking"]["state"];

const labels: Record<State, [string, "neutral" | "success" | "warning" | "danger" | "info"]> = {
  requested: ["Requested", "neutral"],
  confirmed: ["Confirmed", "info"],
  handed_over: ["In use", "warning"],
  returned: ["Returned", "warning"],
  settled: ["Completed", "success"],
  cancelled: ["Cancelled", "neutral"],
  disputed: ["Under review", "danger"],
};

export function BookingStateBadge({ state }: { state: State }) {
  const [label, tone] = labels[state];
  return <Badge tone={tone}>{label}</Badge>;
}
