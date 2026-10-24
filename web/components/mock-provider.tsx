"use client";

import dynamic from "next/dynamic";
import { type ReactNode, useState } from "react";

// msw/browser has no Node build, so it must stay out of the server bundle.
const MockStarter = dynamic(() => import("./mock-starter"), { ssr: false });

/** Starts MSW when NEXT_PUBLIC_API_MOCKS=true so screens work without the API. */
export function MockProvider({ children }: { children: ReactNode }) {
  const enabled = process.env.NEXT_PUBLIC_API_MOCKS === "true";
  const [ready, setReady] = useState(!enabled);
  return (
    <>
      {enabled && <MockStarter onReady={() => setReady(true)} />}
      {ready ? children : null}
    </>
  );
}
