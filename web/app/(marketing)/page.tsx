import Link from "next/link";

import { FeaturedListings } from "@/components/featured-listings";
import { applicationUrl } from "@/lib/application-url";
import { CATEGORIES } from "@/lib/catalogue";

const POPULAR_STATIONS = ["Bishan", "Bugis", "Clementi", "Jurong East", "Tampines", "Woodlands"];

export default function Home() {
  return (
    <>
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
              <Link className="rounded-xl bg-[#f2a65f] px-5 py-4 font-extrabold text-[#17352b]" href={applicationUrl("/search")}>
                Explore items ↗
              </Link>
              <Link className="rounded-xl border border-[#9bbdaf] px-5 py-4 font-extrabold" href={applicationUrl("/listings/new")}>
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
          <form action={applicationUrl("/search")} className="grid gap-3 rounded-2xl border border-[#eae9df] bg-white p-3 shadow-2xl md:grid-cols-[1fr_.7fr_auto]">
            <label className="px-4 py-3 text-xs font-extrabold tracking-wider text-[#6e8a7b]">
              WHAT ARE YOU LOOKING FOR?
              <input className="mt-2 block w-full text-base font-semibold text-[#17352b] outline-none" name="q" placeholder="Try camera, tent, drill…" />
            </label>
            <label className="px-4 py-3 text-xs font-extrabold tracking-wider text-[#6e8a7b]">
              NEAR
              <select className="mt-2 block w-full bg-white text-base font-semibold text-[#17352b] outline-none" name="mrt">
                <option value="">All Singapore</option>
                {POPULAR_STATIONS.map((station) => (
                  <option key={station}>{station}</option>
                ))}
              </select>
            </label>
            <button className="grid place-items-center rounded-xl bg-[#f2a65f] px-7 py-4 font-extrabold" type="submit">
              Search items →
            </button>
          </form>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
          <p className="text-xs font-extrabold tracking-[0.16em] text-[#cb7540]">A LITTLE OF EVERYTHING</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.045em]">What’s your next plan?</h2>
          <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            {CATEGORIES.slice(0, 6).map(({ icon, name }) => (
              <Link
                className="flex min-h-32 flex-col justify-between rounded-2xl border border-[#e8ece3] bg-[#f7f6ef] p-4"
                href={applicationUrl(`/search?category=${encodeURIComponent(name)}`)}
                key={name}
              >
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
            <div className="mt-8">
              <FeaturedListings />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8" id="how-it-works">
          <h2 className="text-4xl font-extrabold tracking-[-0.045em]">Sharing looks good on everyone.</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              ["Find your thing", "Search by MRT station and pick dates; only items free for your dates show up."],
              ["Book with confidence", "Your fee and deposit are held safely. Photos at handover record the item's condition."],
              ["Return and review", "Photos at return settle the deposit fairly. Then rate each other."],
            ].map(([step, text], index) => (
              <article className="rounded-2xl border border-[#e5ece3] bg-white p-7" key={step}>
                <span className="text-sm font-extrabold text-[#cb7540]">0{index + 1}</span>
                <h3 className="mt-8 text-xl font-extrabold">{step}</h3>
                <p className="mt-2 text-sm leading-6 text-[#718477]">{text}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
