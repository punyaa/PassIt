export const SESSION_COOKIE = "passit_session";

/** Development sign-in is on outside production builds, or when PASSIT_DEV_LOGIN=true. */
export function devLoginEnabled(): boolean {
  return process.env.NODE_ENV !== "production" || process.env.PASSIT_DEV_LOGIN === "true";
}
