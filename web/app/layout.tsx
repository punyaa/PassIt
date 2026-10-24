import type { Metadata } from "next";
import type { ReactNode } from "react";

import { MockProvider } from "@/components/mock-provider";
import { SessionProvider } from "@/components/session";

import "./globals.css";

export const metadata: Metadata = {
  title: "PassIt — rent more, own less",
  description: "An island-wide peer-to-peer rental marketplace for Singapore.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <MockProvider>
          <SessionProvider>{children}</SessionProvider>
        </MockProvider>
      </body>
    </html>
  );
}
