import Link from "next/link";

import { AppHeader } from "./app-header";

type ScreenPlaceholderProps = {
  title: string;
  description: string;
  owner: "F1 Front core" | "F2 Front transaction";
};

export function ScreenPlaceholder({ title, description, owner }: ScreenPlaceholderProps) {
  return (
    <>
      <AppHeader />
      <main className="mx-auto max-w-4xl px-5 py-20 lg:px-8">
        <span className="text-xs font-extrabold uppercase tracking-[0.18em] text-[#cb7540]">{owner}</span>
        <h1 className="mt-4 text-5xl font-extrabold tracking-[-0.05em]">{title}</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-[#667c6e]">{description}</p>
        <div className="mt-10 rounded-2xl border border-dashed border-[#b9cdbf] bg-white p-8">
          <strong>Contract-first screen</strong>
          <p className="mt-2 text-sm leading-6 text-[#667c6e]">
            Build this view against the MSW handlers, then switch to the staging API without changing the component contract.
          </p>
        </div>
        <Link className="mt-8 inline-flex rounded-xl bg-[#f2a65f] px-5 py-3 font-bold" href="/">
          Back to prototype shell
        </Link>
      </main>
    </>
  );
}
