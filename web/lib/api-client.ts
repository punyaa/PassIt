import type { components } from "./api-types";

export type Schemas = components["schemas"];

export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Detail = string | { msg: string; loc?: (string | number)[] }[] | { feature?: string; owner?: string };

function describe(status: number, detail: Detail | undefined): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = item.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join("; ");
  }
  if (detail?.feature) return `${detail.feature} is not available yet (${detail.owner}).`;
  return `PassIt API returned ${status}.`;
}

type Query = Record<string, string | number | undefined | null>;

export function withQuery(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const search = params.toString();
  return search ? `${path}?${search}` : path;
}

/** Calls the API with the session cookie. Throws ApiError with a readable message. */
export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init,
      credentials: "include",
      headers: { "content-type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "Can't reach PassIt right now. Check your connection and try again.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    throw new ApiError(response.status, describe(response.status, body?.detail));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
}
