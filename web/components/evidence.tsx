"use client";

import type { Schemas } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";

import { Card } from "./ui";

/** Handover and return evidence side by side (F2). */
export function EvidenceCompare({ checklists }: { checklists: Schemas["ChecklistRecord"][] }) {
  const stages: Schemas["ChecklistRecord"]["stage"][] = ["handover", "return"];
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {stages.map((stage) => {
        const record = checklists.find((c) => c.stage === stage);
        return (
          <Card key={stage}>
            <h3 className="font-extrabold capitalize">{stage}</h3>
            {record ? (
              <>
                <p className="text-xs text-muted">Signed {formatDateTime(record.signed_at)}</p>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {record.media_urls.map((url, index) => (
                    <a className="block aspect-square overflow-hidden rounded-lg border border-line" href={url} key={url} rel="noreferrer" target="_blank">
                      <img alt={`${stage} photo ${index + 1}`} className="size-full object-cover" src={url} />
                    </a>
                  ))}
                </div>
                <ul className="mt-3 space-y-1 text-sm">
                  {record.items.map((item) => (
                    <li key={item.label}>
                      <span className={item.checked ? "text-success" : "text-danger"}>{item.checked ? "✓" : "✗"}</span> {item.label}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-2 text-sm text-muted">Not recorded yet.</p>
            )}
          </Card>
        );
      })}
    </div>
  );
}
