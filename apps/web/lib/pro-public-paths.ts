/**
 * Pro routes that stay open without Pro entitlement during soft launch
 * (and after paywall returns). Matched via proxy `x-pathname`.
 */
const PUBLIC_PRO_PATH_PREFIXES = ["/pro/nfl/launch-notes"] as const;

export function isPublicProPath(
  pathname: string | null | undefined,
): boolean {
  if (!pathname) return false;
  const path = pathname.split("?")[0]?.replace(/\/$/, "") || pathname;
  return PUBLIC_PRO_PATH_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  );
}
