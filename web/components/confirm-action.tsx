"use client";

import { useId, useRef, useState, type ReactNode } from "react";
import { Alert, Button } from "./ui";

/** An inline review step keeps consequential actions in the application's context. */
export function ConfirmAction({
  title,
  description,
  trigger,
  confirmLabel,
  variant,
  onConfirm,
  disabled,
}: {
  title: string;
  description: ReactNode;
  trigger: string;
  confirmLabel: string;
  variant: "primary" | "secondary" | "danger";
  onConfirm: () => Promise<void>;
  disabled: boolean;
}) {
  const regionId = useId();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  function close() {
    if (busy) return;
    setOpen(false);
    setError(null);
    triggerRef.current?.focus();
  }

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      setOpen(false);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Couldn't complete this action. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full">
      <Button
        ref={triggerRef}
        type="button"
        variant={variant}
        disabled={disabled || busy}
        aria-expanded={open}
        aria-controls={open ? regionId : undefined}
        onClick={() => {
          if (open) close();
          else setOpen(true);
        }}
      >
        {trigger}
      </Button>
      {open && (
        <section
          id={regionId}
          role="group"
          aria-label={title}
          aria-busy={busy}
          className="mt-4 space-y-3 rounded-xl border border-line bg-forest-soft p-4"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              close();
            }
          }}
        >
          <h3 className="font-extrabold">{title}</h3>
          <p className="text-sm leading-6 text-muted">{description}</p>
          {error && <Alert>{error}</Alert>}
          <div className="flex flex-wrap gap-3">
            <Button
              autoFocus
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={close}
            >
              Keep reviewing
            </Button>
            <Button
              type="button"
              variant={variant === "danger" ? "danger" : "primary"}
              busy={busy}
              disabled={disabled}
              onClick={confirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
