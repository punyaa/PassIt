export const applicationOrigin = process.env.NEXT_PUBLIC_APP_URL ?? "";

export function applicationUrl(path: string): string {
  return `${applicationOrigin}${path}`;
}
