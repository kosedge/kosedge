import SportProHeader from "@/components/pro/SportProHeader";
import OddsCompareBoard from "@/components/OddsCompareBoard";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

export const dynamic = "force-dynamic";

/**
 * Compare Odds — SSR shell only.
 * Multi-book lines load via client fetch to /api/odds/[sport]/compare
 * so the document HTML is not multi-MB of inlined cells.
 */
export default async function OddsComparePage({
  params,
}: {
  params: Promise<{ sport?: string }> | { sport?: string };
}) {
  const resolved =
    params && typeof (params as Promise<unknown>).then === "function"
      ? await (params as Promise<{ sport?: string }>)
      : ((params as { sport?: string }) ?? {});
  const sportKey = resolveSportKey(resolved?.sport, "nfl");
  const sportName = sportDisplayLabel(sportKey);

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      <SportProHeader activeSport={sportKey} />
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/12 blur-3xl animate-pulse-slow" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 w-full px-5 sm:px-6 pt-6 pb-16 sm:pt-8">
        <OddsCompareBoard sportKey={sportKey} sportName={sportName} />
      </main>
    </div>
  );
}
