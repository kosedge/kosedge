/**
 * Pro routes that stay open without Pro entitlement (desk notes + after paywall).
 * Matched via proxy `x-pathname`.
 */
const PUBLIC_PRO_PATH_PREFIXES = [
  "/pro/nfl/launch-notes",
  "/pro/model-transparency",
] as const;

export function isPublicProPath(
  pathname: string | null | undefined,
): boolean {
  if (!pathname) return false;
  const path = pathname.split("?")[0]?.replace(/\/$/, "") || pathname;
  return PUBLIC_PRO_PATH_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  );
}
