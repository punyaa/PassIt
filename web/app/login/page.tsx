import { Suspense } from "react";

import { LoginForm } from "@/components/auth-forms";
import { PageShell } from "@/components/page-shell";
import { PageHeader } from "@/components/ui";
import { devLoginEnabled } from "@/lib/dev-login";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <PageShell width="max-w-lg">
      <PageHeader eyebrow="Welcome back" title="Log in" />
      <Suspense>
        <LoginForm devLogin={devLoginEnabled()} />
      </Suspense>
    </PageShell>
  );
}
