import { permanentRedirect } from "next/navigation";

function querySuffix(
  searchParams: Record<string, string | string[] | undefined> | undefined,
): string {
  if (!searchParams) return "";
  const qs = new URLSearchParams();
  for (const [key, raw] of Object.entries(searchParams)) {
    if (raw == null) continue;
    if (Array.isArray(raw)) {
      for (const v of raw) {
        if (v != null && v !== "") qs.append(key, v);
      }
    } else if (raw !== "") {
      qs.set(key, raw);
    }
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/**
 * Legacy / mistaken Pro path.
 * Canonical decision center is /edge-board/nfl (next.config also 308s all sports).
 */
export default async function NflEdgeBoardAliasPage({
  searchParams,
}: {
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const sp =
    searchParams &&
    typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<
          Record<string, string | string[] | undefined>
        >)
      : ((searchParams as
          | Record<string, string | string[] | undefined>
          | undefined) ?? undefined);
  permanentRedirect(`/edge-board/nfl${querySuffix(sp)}`);
}
