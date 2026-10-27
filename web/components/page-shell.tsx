import type { ReactNode } from "react";

export function PageShell({
  children,
  width = "max-w-6xl",
}: {
  children: ReactNode;
  width?: string;
}) {
  return (
    <main className={`mx-auto ${width} px-4 py-7 sm:px-6 sm:py-10 lg:px-8`}>
      {children}
    </main>
  );
}
