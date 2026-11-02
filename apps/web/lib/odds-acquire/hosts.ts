/**
 * Sole allowed the-odds-api.com literals in apps/web runtime.
 * CI grep fails if this hostname appears outside lib/odds-acquire/.
 */

export const ODDS_API_HOST = "api.the-odds-api.com";
export const ODDS_WIDGET_HOST = "widget.the-odds-api.com";

export const ODDS_API_ORIGIN = `https://${ODDS_API_HOST}`;
export const ODDS_WIDGET_ORIGIN = `https://${ODDS_WIDGET_HOST}`;

export const ODDS_PAID_HOSTS = [ODDS_API_HOST, ODDS_WIDGET_HOST] as const;

export function isOddsPaidHost(host: string | null | undefined): boolean {
  const h = String(host ?? "")
    .trim()
    .toLowerCase();
  return (
    h === ODDS_API_HOST ||
    h === ODDS_WIDGET_HOST ||
    h.endsWith(".the-odds-api.com")
  );
}

export function isOddsPaidUrl(raw: string | URL): boolean {
  try {
    const url = typeof raw === "string" ? new URL(raw) : raw;
    return isOddsPaidHost(url.hostname);
  } catch {
    return /the-odds-api\.com/i.test(String(raw));
  }
}
