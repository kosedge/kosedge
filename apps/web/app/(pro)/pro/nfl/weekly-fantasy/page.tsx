import Link from "next/link";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import { loadPlayerSeasonTotalsSpine } from "@/lib/nfl-player-season-totals-spine";
import type { PlayerProjectionTotalsRow } from "@/lib/nfl-preseason-artifacts";

type SearchValue = string | string[] | undefined;
type Scoring = "standard" | "half_ppr" | "ppr";

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function fantasyPoints(
  player: PlayerProjectionTotalsRow,
  scoring: Scoring,
): number {
  const recBonus = scoring === "ppr" ? 1 : scoring === "half_ppr" ? 0.5 : 0;
  return (
    player.passYardsTotal / 25 +
    player.passTdsTotal * 4 +
    player.rushYardsTotal / 10 +
    player.rushTdsTotal * 6 +
    player.receivingYardsTotal / 10 +
    player.recTdsTotal * 6 +
    player.receptionsTotal * recBonus
  );
}

function buildHref(base: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(base)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/pro/nfl/weekly-fantasy?${query}` : "/pro/nfl/weekly-fantasy";
}

export default async function NflWeeklyFantasyPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const scoringRaw = (firstValue(search.scoring) ?? "half_ppr").toLowerCase();
  const scoring: Scoring =
    scoringRaw === "standard" || scoringRaw === "ppr" ? scoringRaw : "half_ppr";
  const position = (firstValue(search.pos) ?? "ALL").toUpperCase();

  const bundleSpine = await loadPlayerSeasonTotalsSpine({
    season: 2026,
    limit: 400,
  });
  const players = bundleSpine.rows
    .filter((p) => (position === "ALL" ? true : p.position === position))
    .map((p) => ({
      ...p,
      pts: fantasyPoints(p, scoring),
      ppg:
        p.gamesProjected > 0 ? fantasyPoints(p, scoring) / p.gamesProjected : 0,
    }))
    .sort((a, b) => b.ppg - a.ppg);

  const leaders = players.slice(0, 8);
  const positions = ["ALL", "QB", "RB", "WR", "TE"];

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
          Week · player-production spine
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          Weekly Fantasy Projections
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-kos-text/75">
          Season-rate fantasy points from the shared player-production spine
          (same board as fantasy draft rankings), expressed per game. Research
          surface — not a start/sit service.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href="/pro/nfl/props"
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Player Props Board
          </Link>
          <Link
            href="/pro/nfl/fantasy"
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Fantasy Draft Desk
          </Link>
          <Link
            href="/pro/nfl/dfs"
            className="rounded-lg border border-kos-gold/30 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
          >
            DFS Board
          </Link>
        </div>
      </section>

      <div className="mt-6">
        <HonestStatusBanner
          title="Preseason · not a live weekly slate"
          tone="sky"
        >
          <p>
            These are season-rate PPG figures from the player-production spine —
            not week-specific start/sit ranks. K and DST are not included on
            this surface until weekly fantasy feeds land.
          </p>
        </HonestStatusBanner>
      </div>

      {bundleSpine.rows.length === 0 ? (
        <div className="mt-6">
          <HonestStatusBanner
            title="Player production spine missing"
            tone="amber"
          >
            <p>
              No spine fantasy rankings (or CSV fallback) are available in this
              environment — weekly leaders stay empty until the board loads.
            </p>
          </HonestStatusBanner>
        </div>
      ) : null}

      <section className="mt-6 flex flex-wrap gap-2">
        {(
          [
            ["half_ppr", "Half PPR"],
            ["ppr", "PPR"],
            ["standard", "Standard"],
          ] as const
        ).map(([value, label]) => (
          <Link
            key={value}
            href={buildHref({
              scoring: value,
              pos: position === "ALL" ? undefined : position,
            })}
            className={
              scoring === value
                ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            {label}
          </Link>
        ))}
        <span className="mx-1 text-kos-text/30">|</span>
        {positions.map((pos) => (
          <Link
            key={pos}
            href={buildHref({
              scoring,
              pos: pos === "ALL" ? undefined : pos,
            })}
            className={
              position === pos
                ? "rounded-md border border-edge-green/40 bg-edge-green/10 px-3 py-1.5 text-xs font-semibold text-edge-green"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            {pos}
          </Link>
        ))}
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold text-kos-text">Weekly leaders</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {leaders.map((p, i) => (
            <div
              key={p.playerKey}
              className="rounded-xl border border-white/10 bg-black/35 p-4"
            >
              <p className="text-[11px] text-kos-text/45">#{i + 1}</p>
              <p className="mt-1 font-semibold text-kos-text">{p.playerName}</p>
              <p className="text-xs text-kos-text/55">
                {p.position} · {p.team}
              </p>
              <p className="mt-2 text-lg font-semibold text-kos-gold">
                {p.ppg.toFixed(1)}{" "}
                <span className="text-xs font-normal text-kos-text/50">
                  PPG
                </span>
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/60">
              <th className="px-3 py-3">Rank</th>
              <th className="px-3 py-3">Player</th>
              <th className="px-3 py-3">Pos</th>
              <th className="px-3 py-3">Team</th>
              <th className="px-3 py-3">PPG</th>
              <th className="px-3 py-3">Season Pts</th>
              <th className="px-3 py-3">Games</th>
            </tr>
          </thead>
          <tbody>
            {players.slice(0, 150).map((p, i) => (
              <tr
                key={p.playerKey}
                className="border-b border-white/5 odd:bg-white/[0.02]"
              >
                <td className="px-3 py-2 text-kos-text/70">{i + 1}</td>
                <td className="px-3 py-2 font-medium text-kos-text">
                  {p.playerName}
                </td>
                <td className="px-3 py-2 text-kos-text/70">{p.position}</td>
                <td className="px-3 py-2">
                  <Link
                    href={`/pro/nfl/teams/${p.team}/overview`}
                    className="text-kos-gold/90 hover:text-kos-gold"
                  >
                    {p.team}
                  </Link>
                </td>
                <td className="px-3 py-2 font-semibold text-kos-gold">
                  {p.ppg.toFixed(1)}
                </td>
                <td className="px-3 py-2 text-kos-text/75">
                  {p.pts.toFixed(1)}
                </td>
                <td className="px-3 py-2 text-kos-text/60">
                  {p.gamesProjected}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {players.length === 0 ? (
          <div className="p-6">
            <HonestStatusBanner title="No rows for this filter" tone="neutral">
              <p>
                No skill-position projection rows matched. Try ALL / another
                position, or wait for the player-production spine to load.
              </p>
            </HonestStatusBanner>
          </div>
        ) : null}
      </section>
    </main>
  );
}
