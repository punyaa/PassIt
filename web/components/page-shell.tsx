import type { ReactNode } from "react";

import { AppHeader } from "./app-header";

export function PageShell({ children, width = "max-w-6xl" }: { children: ReactNode; width?: string }) {
  return (
    <>
      <AppHeader />
      <main className={`mx-auto ${width} px-5 py-12 lg:px-8`}>{children}</main>
    </>
  );
}
