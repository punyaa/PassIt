"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { apiPost, type Schemas } from "@/lib/api-client";
import { uploadMedia } from "@/lib/uploads";

import { PhotoPicker } from "./photo-picker";
import { Alert, Button, Card, Input } from "./ui";

type Stage = "handover" | "return";

const DEFAULT_ITEMS: Record<Stage, string[]> = {
  handover: ["Item is clean", "All parts and accessories included", "Works as described", "No visible damage"],
  return: ["Item is clean", "All parts and accessories returned", "Still works", "No new damage"],
};

/** Condition checklist plus photo evidence for a handover or a return (F2). */
export function ChecklistForm({ booking, stage }: { booking: Schemas["Booking"]; stage: Stage }) {
  const router = useRouter();
  const [items, setItems] = useState(DEFAULT_ITEMS[stage].map((label) => ({ label, checked: false })));
  const [custom, setCustom] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [agreed, setAgreed] = useState(false);
  const [progress, setProgress] = useState<string>();
  const [error, setError] = useState<string>();

  function addItem() {
    const label = custom.trim();
    if (!label || items.some((item) => item.label === label)) return;
    setItems((current) => [...current, { label, checked: false }]);
    setCustom("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!photos.length) return setError("Add at least one photo of the item.");
    setError(undefined);
    try {
      const keys: string[] = [];
      for (const [index, file] of photos.entries()) {
        setProgress(`Uploading photo ${index + 1} of ${photos.length}…`);
        keys.push(await uploadMedia(file, stage));
      }
      setProgress("Saving checklist…");
      await apiPost<Schemas["Booking"]>(`/bookings/${booking.id}/${stage}`, { items, media_keys: keys });
      router.push(`/bookings/${booking.id}`);
    } catch (caught) {
      setProgress(undefined);
      setError(caught instanceof Error ? caught.message : "Couldn't save the checklist.");
    }
  }

  const unchecked = items.filter((item) => !item.checked).length;

  return (
    <form className="space-y-6" onSubmit={submit}>
      <Card className="space-y-4">
        <h2 className="text-xl font-extrabold">1. Photograph the item</h2>
        <p className="text-sm leading-6 text-muted">
          Take clear photos from several angles, including any existing marks. Photos are stored permanently as evidence.
        </p>
        <PhotoPicker capture files={photos} label="Take photo" max={10} onChange={setPhotos} />
      </Card>

      <Card className="space-y-4">
        <h2 className="text-xl font-extrabold">2. Check its condition</h2>
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li key={item.label}>
              <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-line p-3 has-checked:border-forest has-checked:bg-forest-soft">
                <input
                  checked={item.checked}
                  className="size-5 accent-forest"
                  onChange={(e) =>
                    setItems((current) => current.map((it, i) => (i === index ? { ...it, checked: e.target.checked } : it)))
                  }
                  type="checkbox"
                />
                <span className="font-bold">{item.label}</span>
              </label>
            </li>
          ))}
        </ul>
        <div className="flex gap-2">
          <Input
            aria-label="Add a checklist item"
            maxLength={200}
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addItem();
              }
            }}
            placeholder="Add an item, e.g. Charger included"
            value={custom}
          />
          <Button onClick={addItem} type="button" variant="secondary">
            Add
          </Button>
        </div>
        {unchecked > 0 && (
          <p className="text-xs text-muted">
            {unchecked} item{unchecked === 1 ? "" : "s"} left unticked will be recorded as not OK.
          </p>
        )}
      </Card>

      <Card className="space-y-4">
        <h2 className="text-xl font-extrabold">3. Confirm together</h2>
        <label className="flex items-start gap-3 text-sm leading-6">
          <input checked={agreed} className="mt-1 size-5 accent-forest" onChange={(e) => setAgreed(e.target.checked)} type="checkbox" />
          Both the borrower and the lender have seen the item and agree these photos and the checklist describe its
          condition {stage === "handover" ? "at handover" : "on return"}.
        </label>
        {error && <Alert>{error}</Alert>}
        <div className="flex items-center justify-end gap-4">
          {progress && <span className="text-sm text-muted">{progress}</span>}
          <Button busy={Boolean(progress)} disabled={!agreed} type="submit" variant="accent">
            {stage === "handover" ? "Confirm handover" : "Confirm return"}
          </Button>
        </div>
      </Card>
    </form>
  );
}
