"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";

import { ApiError } from "@/lib/api-client";
import { devSignIn, logIn, signUp } from "@/lib/auth";

import { useSession } from "./session";
import { Alert, Button, Card, Field, Input, Textarea } from "./ui";

function useAfterSignIn() {
  const router = useRouter();
  const next = useSearchParams().get("next");
  const { refresh } = useSession();
  return async () => {
    await refresh();
    router.push(next?.startsWith("/") ? next : "/search");
  };
}

function authMessage(error: unknown): string {
  if (error instanceof ApiError && (error.status === 501 || error.status === 404)) {
    return "Email accounts aren't live yet. Use a demo session below for now.";
  }
  if (error instanceof ApiError && error.status === 401) return "That email and password don't match.";
  return error instanceof Error ? error.message : "Something went wrong.";
}

export function LoginForm({ devLogin }: { devLogin: boolean }) {
  const afterSignIn = useAfterSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      await logIn(email, password);
      await afterSignIn();
    } catch (caught) {
      setError(authMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <form className="space-y-5" onSubmit={submit}>
          <Field label="Email">
            <Input autoComplete="email" onChange={(e) => setEmail(e.target.value)} required type="email" value={email} />
          </Field>
          <Field label="Password">
            <Input
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              required
              type="password"
              value={password}
            />
          </Field>
          {error && <Alert>{error}</Alert>}
          <Button busy={busy} className="w-full" type="submit">
            Log in
          </Button>
          <p className="text-center text-sm text-muted">
            New to PassIt?{" "}
            <Link className="font-bold text-ink underline" href="/signup">
              Create an account
            </Link>
          </p>
        </form>
      </Card>
      {devLogin && <DevSessionForm onSignedIn={afterSignIn} />}
    </div>
  );
}

function DevSessionForm({ onSignedIn }: { onSignedIn: () => Promise<void> }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      await devSignIn(token);
      await onSignedIn();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="border-dashed bg-sand">
      <form className="space-y-4" onSubmit={submit}>
        <div>
          <strong>Demo session</strong>
          <p className="mt-1 text-sm leading-6 text-muted">
            Development only. Paste a token printed by{" "}
            <code className="rounded bg-white px-1">python -m scripts.seed</code>.
          </p>
        </div>
        <Textarea
          aria-label="Session token"
          className="min-h-20 font-mono text-xs"
          onChange={(e) => setToken(e.target.value)}
          placeholder="Bearer eyJhbGciOi…"
          required
          value={token}
        />
        {error && <Alert>{error}</Alert>}
        <Button busy={busy} type="submit" variant="secondary">
          Use demo session
        </Button>
      </form>
    </Card>
  );
}

export function SignupForm() {
  const afterSignIn = useAfterSignIn();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const update = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((current) => ({ ...current, [key]: e.target.value }));
  const mismatch = form.confirm.length > 0 && form.password !== form.confirm;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mismatch) return;
    setBusy(true);
    setError(undefined);
    try {
      await signUp(form.name.trim(), form.email, form.password);
      await afterSignIn();
    } catch (caught) {
      setError(authMessage(caught).replace(" below", " on the log-in page"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <form className="space-y-5" onSubmit={submit}>
        <Field label="Display name" hint="Shown to people you rent with.">
          <Input autoComplete="name" maxLength={60} onChange={update("name")} required value={form.name} />
        </Field>
        <Field label="Email">
          <Input autoComplete="email" onChange={update("email")} required type="email" value={form.email} />
        </Field>
        <Field label="Password" hint="At least 8 characters.">
          <Input
            autoComplete="new-password"
            minLength={8}
            onChange={update("password")}
            required
            type="password"
            value={form.password}
          />
        </Field>
        <Field label="Confirm password" error={mismatch ? "Passwords don't match." : undefined}>
          <Input
            autoComplete="new-password"
            onChange={update("confirm")}
            required
            type="password"
            value={form.confirm}
          />
        </Field>
        {error && <Alert>{error}</Alert>}
        <Button busy={busy} className="w-full" disabled={mismatch} type="submit">
          Create account
        </Button>
        <p className="text-center text-sm text-muted">
          Already have an account?{" "}
          <Link className="font-bold text-ink underline" href="/login">
            Log in
          </Link>
        </p>
      </form>
    </Card>
  );
}
