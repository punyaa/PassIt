import type { ReactNode } from "react";

export function Avatar({
  name,
  url,
  large,
}: {
  name: string;
  url: string | null;
  large: boolean;
}): ReactNode {
  return (
    <span
      className={`grid shrink-0 place-items-center overflow-hidden rounded-full bg-sage font-bold ${large ? "size-20 text-3xl" : "size-11 text-base"}`}
      aria-hidden="true"
    >
      {url ? (
        <img alt="" src={url} className="size-full object-cover" />
      ) : (
        name
          .trim()
          .split(/\s+/)
          .map((part) => part[0])
          .slice(0, 2)
          .join("")
          .toUpperCase()
      )}
    </span>
  );
}
