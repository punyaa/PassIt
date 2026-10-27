"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { ApiError, apiRequest, type Schemas } from "@/lib/api-client";
import { logOut } from "@/lib/auth";

import { LinkButton, Spinner } from "./ui";

export type SessionUser = Schemas["CurrentUserResponse"];

type SessionState = {
  user: SessionUser | null;
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setUser(await apiRequest<SessionUser>("/auth/me"));
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401)
        console.warn(error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    await logOut();
    setUser(null);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <SessionContext value={{ user, loading, refresh, signOut }}>
      {children}
    </SessionContext>
  );
}

export function useSession(): SessionState {
  const session = useContext(SessionContext);
  if (!session)
    throw new Error("useSession must be used inside SessionProvider");
  return session;
}

/** Renders children only for signed-in users; otherwise a sign-in prompt.
 * Server pages pass elements; client pages may pass a render function to get the user. */
export function RequireAuth({
  children,
}: {
  children: ReactNode | ((user: SessionUser) => ReactNode);
}) {
  const { user, loading } = useSession();
  const pathname = usePathname();
  if (loading) {
    return (
      <div className="py-20 text-center">
        <Spinner label="Checking your session…" />
      </div>
    );
  }
  if (!user) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <h1 className="text-3xl font-extrabold tracking-[-0.04em]">
          Sign in to continue
        </h1>
        <p className="mt-3 text-muted">
          You need a PassIt account to see this page.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <LinkButton href={`/login?next=${encodeURIComponent(pathname)}`}>
            Log in
          </LinkButton>
          <Link
            className="self-center text-sm font-bold underline"
            href="/signup"
          >
            Create an account
          </Link>
        </div>
      </div>
    );
  }
  return <>{typeof children === "function" ? children(user) : children}</>;
}
