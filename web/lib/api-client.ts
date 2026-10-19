const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: { "content-type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new Error(`PassIt API returned ${response.status}.`);
  }
  return response.json() as Promise<T>;
}
