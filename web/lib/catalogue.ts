export const CATEGORIES = [
  { name: "Outdoor", icon: "⛺" },
  { name: "Events", icon: "🎉" },
  { name: "Tools", icon: "🛠️" },
  { name: "Baby & kids", icon: "🧸" },
  { name: "Electronics", icon: "📷" },
  { name: "Home", icon: "🪴" },
  { name: "Mobility", icon: "🛴" },
  { name: "Travel", icon: "🧳" },
] as const;

export const CONDITIONS = ["New", "Like new", "Good", "Fair", "Worn"] as const;

export function categoryIcon(category: string): string {
  return CATEGORIES.find((item) => item.name === category)?.icon ?? "📦";
}
