"use client";

import { useEffect, useState } from "react";

import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES } from "@/lib/uploads";

/**
 * Pick or capture photos. On phones `capture` opens the camera directly, which is
 * what handover and return need; listing photos can come from the library.
 */
export function PhotoPicker({
  files,
  onChange,
  max = 6,
  capture = false,
  label = "Add photos",
}: {
  files: File[];
  onChange: (files: File[]) => void;
  max?: number;
  capture?: boolean;
  label?: string;
}) {
  const [previews, setPreviews] = useState<string[]>([]);
  const [error, setError] = useState<string>();

  useEffect(() => {
    const urls = files.map((file) => URL.createObjectURL(file));
    setPreviews(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [files]);

  function add(list: FileList | null) {
    const picked = Array.from(list ?? []);
    const rejected = picked.filter(
      (file) =>
        !ACCEPTED_TYPES.includes(file.type as never) ||
        file.size > MAX_UPLOAD_BYTES,
    );
    setError(
      rejected.length ? "Use JPEG or PNG photos under 10 MB." : undefined,
    );
    const accepted = picked.filter((file) => !rejected.includes(file));
    onChange([...files, ...accepted].slice(0, max));
  }

  return (
    <div>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
        {previews.map((url, index) => (
          <div
            className="relative aspect-square overflow-hidden rounded-xl border border-line"
            key={url}
          >
            <img
              alt={`Photo ${index + 1}`}
              className="size-full object-cover"
              src={url}
            />
            <button
              aria-label={`Remove photo ${index + 1}`}
              className="absolute right-1 top-1 grid size-7 place-items-center rounded-full bg-white/90 text-sm font-bold shadow"
              onClick={() => onChange(files.filter((_, i) => i !== index))}
              type="button"
            >
              ×
            </button>
          </div>
        ))}
        {files.length < max && (
          <label className="grid aspect-square cursor-pointer place-items-center rounded-xl border-2 border-dashed border-[#b9cdbf] bg-sand text-center text-xs font-bold text-muted hover:border-forest has-focus-visible:outline-2 has-focus-visible:outline-forest">
            <span>
              <span className="block text-2xl">📷</span>
              {label}
            </span>
            <input
              accept={ACCEPTED_TYPES.join(",")}
              capture={capture ? "environment" : undefined}
              className="sr-only"
              multiple
              onChange={(e) => {
                add(e.target.files);
                e.target.value = "";
              }}
              type="file"
            />
          </label>
        )}
      </div>
      {error && <p className="mt-2 text-xs font-bold text-danger">{error}</p>}
      <p className="mt-2 text-xs text-muted">
        {files.length} of {max} photos
      </p>
    </div>
  );
}
