import Link from "next/link";
import SportProShell from "@/components/pro/SportProShell";
import { getKeiCode, getKeiProductLabel } from "@/lib/kei-brand";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import { getKeiLines } from "@/lib/kei-lines";
import { sportIsMarketsOnlyEdgeBoard } from "@/lib/edge-board-kei-availability";
import { KeiLinesTable } from "./KeiLinesTable";
import { NcaamKeiLinesClient } from "./NcaamKeiLinesClient";

export const dynamic = "force-dynamic";

export default async function KeiLinesSportPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const sportName = sportDisplayLabel(sportKey);
  const keiCode = getKeiCode(sportKey);
  const games = getKeiLines(sportKey);
  const isNcaam = sportKey === "ncaam";

  return (
    <SportProShell
      sport={sportKey}
      pageTitle={`${sportName} — ${keiCode} Lines`}
      pageSubtitle={`${getKeiProductLabel(sportKey)}. ${
        sportIsMarketsOnlyEdgeBoard(sportKey)
          ? "No KEI handicap on this sport yet — this table stays empty (no invented lines). Use Edge Board for sportsbook Open/Best."
          : isNcaam
            ? "Projected spread and over/under by game date. Use the dropdown to pick a day."
            : "Projected spread and over/under for each game."
      } Research baselines — not picks.`}
      actions={
        <Link
          href="/pro/kei-lines"
          className="min-h-11 inline-flex items-center rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          All sports
        </Link>
      }
    >
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {isNcaam ? (
          <NcaamKeiLinesClient games={games} sportName={sportName} />
        ) : (
          <KeiLinesTable
            games={games}
            sportName={sportName}
            marketsOnly={sportIsMarketsOnlyEdgeBoard(sportKey)}
          />
        )}
      </main>
    </SportProShell>
  );
}
