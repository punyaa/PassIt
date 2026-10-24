"use client";

import { useEffect } from "react";

import { worker } from "@/mocks/browser";

export default function MockStarter({ onReady }: { onReady: () => void }) {
  useEffect(() => {
    void worker.start().then(onReady);
  }, [onReady]);
  return null;
}
