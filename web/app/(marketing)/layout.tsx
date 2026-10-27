import type { ReactNode } from "react";

import { MarketingHeader } from "@/components/marketing-header";

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="bg-[#173f30] px-4 py-2 text-center text-xs font-bold text-[#f7e6bd]">
        The things you need, from people nearby. <span className="text-[#b8d4c0]">Singapore prototype</span>
      </div>
      <MarketingHeader />
      {children}
    </>
  );
}
