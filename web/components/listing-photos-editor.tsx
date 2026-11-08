"use client";

import { useState, type FormEvent } from "react";
import { apiRequest, type Schemas } from "@/lib/api-client";
import { uploadMedia } from "@/lib/uploads";
import { PhotoPicker } from "./photo-picker";
import { Alert, Badge, Button, Card } from "./ui";

type Photo = { key: string; url: string };
const photosOf = (listing: Schemas["ListingDetail"]): Photo[] =>
  (listing.photo_keys ?? []).map((key, index) => ({
    key,
    url: listing.photo_urls?.[index] ?? "",
  }));

export function ListingPhotosEditor({
  listing,
  onSave,
}: {
  listing: Schemas["ListingDetail"];
  onSave: (listing: Schemas["ListingDetail"]) => void;
}) {
  const [photos, setPhotos] = useState<Photo[]>(photosOf(listing));
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  function move(index: number, next: number) {
    setSaved(false);
    setPhotos((current) => {
      const reordered = [...current];
      const [photo] = reordered.splice(index, 1);
      reordered.splice(next, 0, photo);
      return reordered;
    });
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      const keys = photos.map((photo) => photo.key);
      for (const file of files) keys.push(await uploadMedia(file, "listing"));
      const updated = await apiRequest<Schemas["ListingDetail"]>(
        `/listings/${listing.id}`,
        { method: "PATCH", body: JSON.stringify({ photo_keys: keys }) },
      );
      setPhotos(photosOf(updated));
      setFiles([]);
      onSave(updated);
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Couldn't save photos.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="mt-6" onSubmit={submit}>
      <Card className="space-y-5">
        <h2 className="text-xl font-bold">Listing photos</h2>
        <p className="text-sm text-muted">
          The first photo is the cover. Removing listing photos leaves rental
          condition evidence untouched.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {photos.map((photo, index) => (
            <div
              key={photo.key}
              className="overflow-hidden rounded-xl border border-line"
            >
              <img
                src={photo.url}
                alt={`Listing photo ${index + 1}`}
                className="aspect-square w-full object-cover"
              />
              <div className="space-y-2 p-2">
                {index === 0 ? (
                  <Badge tone="success">Cover</Badge>
                ) : (
                  <Button
                    className="w-full px-2 py-2"
                    variant="secondary"
                    type="button"
                    onClick={() => move(index, 0)}
                    disabled={busy}
                  >
                    Make cover
                  </Button>
                )}
                <div className="flex gap-1">
                  <Button
                    className="flex-1 px-2 py-2"
                    type="button"
                    variant="ghost"
                    aria-label={`Move photo ${index + 1} earlier`}
                    disabled={index === 0 || busy}
                    onClick={() => move(index, index - 1)}
                  >
                    ←
                  </Button>
                  <Button
                    className="flex-1 px-2 py-2"
                    type="button"
                    variant="ghost"
                    aria-label={`Move photo ${index + 1} later`}
                    disabled={index === photos.length - 1 || busy}
                    onClick={() => move(index, index + 1)}
                  >
                    →
                  </Button>
                </div>
                <Button
                  className="w-full px-2 py-2"
                  type="button"
                  variant="secondary"
                  aria-label={`Remove listing photo ${index + 1}`}
                  disabled={busy}
                  onClick={() => {
                    setSaved(false);
                    setPhotos((current) =>
                      current.filter((_, i) => i !== index),
                    );
                  }}
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
        {photos.length < 10 && (
          <PhotoPicker
            files={files}
            max={10 - photos.length}
            onChange={(next) => {
              setFiles(next);
              setSaved(false);
            }}
          />
        )}
        {error && <Alert>{error}</Alert>}
        {saved && <Alert tone="success">Photos saved.</Alert>}
        <Button type="submit" busy={busy}>
          Save photos
        </Button>
      </Card>
    </form>
  );
}
