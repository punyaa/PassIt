import type { ReactNode } from "react";

export function PageShell({ children, width = "max-w-6xl" }: { children: ReactNode; width?: string }) {
  return (
    <main className={`mx-auto ${width} px-5 py-12 lg:px-8`}>{children}</main>
  );
}
