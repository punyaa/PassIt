import Link from "next/link";

export function Brand({ href }: { href: string }) {
  return (
    <Link className="flex items-center gap-3 text-2xl font-extrabold tracking-[-0.06em]" href={href}>
      <span className="grid size-9 -rotate-6 place-items-center rounded-xl bg-orange">↗</span>
      <span>
        Pass<span className="text-[#d8793f]">It</span>
        <small className="block text-[8px] tracking-[0.22em] text-[#577364]">RENT • SHARE • REPEAT</small>
      </span>
    </Link>
  );
}
