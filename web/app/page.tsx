import Link from "next/link";

import { AppHeader } from "@/components/app-header";

const categories = [
  ["⛺", "Outdoor"],
  ["🎉", "Events"],
  ["🛠️", "Tools"],
  ["🧸", "Baby & kids"],
  ["📷", "Electronics"],
  ["🪴", "Home"],
];

const listings = [
  ["📷", "Fujifilm camera kit", "Bishan", "S$28"],
  ["⛺", "4-person camping tent", "Clementi", "S$12"],
  ["🛠️", "Cordless drill set", "Queenstown", "S$9"],
  ["📽️", "Portable projector", "Bugis", "S$22"],
];

export default function Home() {
  return (
    <>
      <div className="bg-[#173f30] px-4 py-2 text-center text-xs font-bold text-[#f7e6bd]">
        The things you need, from people nearby. <span className="text-[#b8d4c0]">Singapore prototype</span>
      </div>
      <AppHeader />
      <main>
        <section className="mx-auto mt-7 grid max-w-7xl overflow-hidden rounded-3xl bg-[#194b37] text-white lg:grid-cols-[1.1fr_.9fr]">
          <div className="px-7 py-14 lg:px-14 lg:py-20">
            <span className="text-xs font-extrabold tracking-[0.16em] text-[#d7edcc]">● THE NEIGHBOURHOOD RENTAL CLUB</span>
            <h1 className="mt-6 text-5xl font-extrabold leading-[1.03] tracking-[-0.055em] lg:text-6xl">
              Why buy it when you can <span className="text-[#f3b771]">borrow the moment?</span>
            </h1>
            <p className="mt-5 max-w-xl leading-7 text-[#ccdfd1]">
              Rent useful things from people around you. Spend less, store less, and give good items another adventure.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link className="rounded-xl bg-[#f2a65f] px-5 py-4 font-extrabold text-[#17352b]" href="/search">
                Explore items ↗
              </Link>
              <Link className="rounded-xl border border-[#9bbdaf] px-5 py-4 font-extrabold" href="/listings/new">
                Earn from your items
              </Link>
            </div>
          </div>
          <div className="relative hidden min-h-[470px] place-items-center overflow-hidden bg-[#d5dfb5] lg:grid">
            <div className="absolute size-[430px] rounded-full border border-dashed border-[#476b54]/40" />
            <span className="relative -rotate-12 text-[190px] drop-shadow-xl">📷</span>
            <div className="absolute bottom-12 right-10 rotate-3 rounded-2xl bg-white px-5 py-4 text-sm font-bold text-[#17352b] shadow-xl">
              More doing. Less owning.
            </div>
          </div>
        </section>

        <section className="mx-auto -mt-7 max-w-6xl px-5">
          <form className="grid gap-3 rounded-2xl border border-[#eae9df] bg-white p-3 shadow-2xl md:grid-cols-[1fr_.7fr_auto]">
            <label className="px-4 py-3 text-xs font-extrabold tracking-wider text-[#6e8a7b]">
              WHAT ARE YOU LOOKING FOR?
              <input className="mt-2 block w-full text-base font-semibold text-[#17352b] outline-none" placeholder="Try camera, tent, drill…" />
            </label>
            <label className="px-4 py-3 text-xs font-extrabold tracking-wider text-[#6e8a7b]">
              NEAR
              <select className="mt-2 block w-full bg-white text-base font-semibold text-[#17352b] outline-none">
                <option>All Singapore</option>
                <option>Bishan</option>
                <option>Clementi</option>
              </select>
            </label>
            <Link className="grid place-items-center rounded-xl bg-[#f2a65f] px-7 py-4 font-extrabold" href="/search">
              Search items →
            </Link>
          </form>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
          <p className="text-xs font-extrabold tracking-[0.16em] text-[#cb7540]">A LITTLE OF EVERYTHING</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.045em]">What’s your next plan?</h2>
          <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            {categories.map(([icon, name]) => (
              <Link className="flex min-h-32 flex-col justify-between rounded-2xl border border-[#e8ece3] bg-[#f7f6ef] p-4" href="/search" key={name}>
                <span className="text-3xl">{icon}</span>
                <strong className="text-sm">{name}</strong>
              </Link>
            ))}
          </div>
        </section>

        <section className="bg-[#f3f7f0] py-20">
          <div className="mx-auto max-w-7xl px-5 lg:px-8">
            <p className="text-xs font-extrabold tracking-[0.16em] text-[#cb7540]">DISCOVER & DO MORE</p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.045em]">Things to rent around you.</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {listings.map(([icon, name, area, price]) => (
                <Link className="overflow-hidden rounded-2xl border border-[#e4ebe1] bg-white shadow-sm" href="/listings/sample" key={name}>
                  <div className="grid h-44 place-items-center bg-gradient-to-br from-[#aacbb8] to-[#d9e7bc] text-7xl">{icon}</div>
                  <div className="p-5">
                    <h3 className="min-h-12 text-lg font-extrabold">{name}</h3>
                    <p className="text-sm text-[#718477]">⌖ {area}</p>
                    <div className="mt-4 border-t border-[#edf0e9] pt-3 text-xl font-extrabold">
                      {price} <small className="text-xs font-normal text-[#718477]">/ day</small>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8" id="how-it-works">
          <h2 className="text-4xl font-extrabold tracking-[-0.045em]">Sharing looks good on everyone.</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {["Find your thing", "Book with confidence", "Return and review"].map((step, index) => (
              <article className="rounded-2xl border border-[#e5ece3] bg-white p-7" key={step}>
                <span className="text-sm font-extrabold text-[#cb7540]">0{index + 1}</span>
                <h3 className="mt-8 text-xl font-extrabold">{step}</h3>
                <p className="mt-2 text-sm leading-6 text-[#718477]">A clear, evidence-backed step in the PassIt rental journey.</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
