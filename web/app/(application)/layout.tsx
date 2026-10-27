import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";
import { SessionProvider } from "@/components/session";

export default function ApplicationLayout({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <div className="application-surface">
        <AppHeader />
        <div id="app-content" tabIndex={-1}>{children}</div>
      </div>
    </SessionProvider>
  );
}
