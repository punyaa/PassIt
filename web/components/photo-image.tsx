"use client";

import { useState } from "react";

/**
 * A listing photo that prefers a small thumbnail and quietly falls back to the original.
 *
 * Thumbnails are made by a Lambda a moment after an upload, so one can briefly be missing
 * (and local development has none). When `src` fails to load, the image switches once to
 * `fallbackSrc` instead of showing a broken picture.
 */
export function PhotoImage({
  src,
  fallbackSrc,
  alt,
  className,
}: {
  src: string;
  fallbackSrc?: string;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const shown = failed && fallbackSrc ? fallbackSrc : src;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- remote CloudFront images, no optimiser
    <img
      alt={alt}
      className={className}
      decoding="async"
      loading="lazy"
      onError={() => {
        if (!failed && fallbackSrc && fallbackSrc !== src) setFailed(true);
      }}
      src={shown}
    />
  );
}
