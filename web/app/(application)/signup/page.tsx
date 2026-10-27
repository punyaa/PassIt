import { Suspense } from "react";

import { SignupForm } from "@/components/auth-forms";
import { PageShell } from "@/components/page-shell";
import { PageHeader } from "@/components/ui";

export default function SignupPage() {
  return (
    <PageShell width="max-w-lg">
      <PageHeader
        eyebrow="Join PassIt"
        title="Create your account"
        description="Borrow what you need from neighbours, or earn from things you rarely use."
      />
      <Suspense>
        <SignupForm />
      </Suspense>
    </PageShell>
  );
}
