import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

/* Shared PassIt primitives (Front core). F2 screens import these rather than restyling. */

type Variant = "primary" | "secondary" | "accent" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-forest text-white hover:bg-forest-light",
  accent: "bg-orange text-ink hover:brightness-95",
  secondary: "border border-line bg-white text-ink hover:bg-sand",
  ghost: "text-ink hover:bg-sand",
  danger: "bg-danger text-white hover:brightness-110",
};

export function buttonClass(variant: Variant = "primary", extra = "") {
  return `inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-extrabold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${extra}`;
}

export function Button({
  variant = "primary",
  busy = false,
  className = "",
  children,
  disabled,
  ...props
}: ComponentProps<"button"> & { variant?: Variant; busy?: boolean }) {
  return (
    <button className={buttonClass(variant, className)} disabled={disabled || busy} {...props}>
      {busy && <Spinner />}
      {children}
    </button>
  );
}

export function LinkButton({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={buttonClass(variant, className)} {...props} />;
}

export function Card({ className = "", ...props }: ComponentProps<"div">) {
  return <div className={`rounded-card border border-line bg-white p-5 sm:p-6 ${className}`} {...props} />;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-orange-deep">{eyebrow}</p>
        )}
        <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.045em] sm:text-4xl">{title}</h1>
        {description && <p className="mt-3 max-w-2xl leading-7 text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </div>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: ReactNode;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-extrabold">{label}</span>
      <div className="mt-2">{children}</div>
      {hint && !error && <span className="mt-1 block text-xs text-muted">{hint}</span>}
      {error && <span className="mt-1 block text-xs font-bold text-danger">{error}</span>}
    </label>
  );
}

const control =
  "block w-full rounded-xl border border-line bg-white px-4 py-3 text-base text-ink outline-none transition focus:border-forest";

export function Input({ className = "", ...props }: ComponentProps<"input">) {
  return <input className={`${control} ${className}`} {...props} />;
}

export function Select({ className = "", ...props }: ComponentProps<"select">) {
  return <select className={`${control} ${className}`} {...props} />;
}

export function Textarea({ className = "", ...props }: ComponentProps<"textarea">) {
  return <textarea className={`${control} min-h-28 ${className}`} {...props} />;
}

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

const tones: Record<Tone, string> = {
  neutral: "bg-sand text-muted",
  success: "bg-success-soft text-success",
  warning: "bg-[#fdf1e4] text-orange-deep",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-[#2c5a78]",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-extrabold ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function Alert({
  tone = "danger",
  title,
  children,
}: {
  tone?: Exclude<Tone, "neutral" | "warning">;
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={`rounded-xl px-4 py-3 text-sm ${tones[tone]}`}>
      {title && <strong className="block">{title}</strong>}
      {children}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted" role="status">
      <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      {label}
    </span>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-[#b9cdbf] bg-white p-10 text-center">
      <strong className="text-lg">{title}</strong>
      {children && <div className="mt-2 text-sm leading-6 text-muted">{children}</div>}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card>
      <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-3 text-3xl font-extrabold tracking-[-0.04em]">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </Card>
  );
}
