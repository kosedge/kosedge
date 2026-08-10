import Link from "next/link";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import {
  loadLatestNflPreseasonBundle2026,
  type PlayerProjectionTotalsRow,
} from "@/lib/nfl-preseason-artifacts";

type SearchValue = string | string[] | undefined;
type Site = "dk" | "fd";

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

/** Half-PPR fantasy points — research projection used for the DFS board. */
function projPoints(player: PlayerProjectionTotalsRow): number {
  return (
    player.passYardsTotal / 25 +
    player.passTdsTotal * 4 +
    player.rushYardsTotal / 10 +
    player.rushTdsTotal * 6 +
    player.receivingYardsTotal / 10 +
    player.recTdsTotal * 6 +
    player.receptionsTotal * 0.5
  );
}

function buildHref(site: Site): string {
  return site === "dk" ? "/pro/nfl/dfs" : "/pro/nfl/dfs?site=fd";
}

export default async function NflDfsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const site: Site = firstValue(search.site) === "fd" ? "fd" : "dk";
  const bundle = loadLatestNflPreseasonBundle2026();

  const rows = (bundle?.playerTotalsRegular ?? [])
    .filter((p) => ["QB", "RB", "WR", "TE"].includes(p.position))
    .map((p) => {
      const seasonPts = projPoints(p);
      const proj =
        p.gamesProjected > 0 ? seasonPts / p.gamesProjected : seasonPts;
      const ceiling = proj * 1.35;
      return {
        ...p,
        proj,
        ceiling,
        salary: null as number | null,
        value: null as number | null,
        own: null as number | null,
        opp: null as string | null,
      };
    })
    .sort((a, b) => b.proj - a.proj);

  const topProj = rows.slice(0, 5);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
          DFS research desk
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          DFS Board
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-kos-text/75">
          Projection research for {site === "dk" ? "DraftKings" : "FanDuel"}.
          Salary, ownership, and opponent fill when official slate feeds are
          live — projections come from the Kos Edge player model.
        </p>
        <div className="mt-4">
          <HonestStatusBanner title="Preseason · slate fields empty" tone="sky">
            <p>
              Opp, Salary, Value, and Own% stay blank until a live DFS slate
              connects. Skill-position projections/ceilings below are season-rate
              from the model — not a priced contest slate. K/DST omitted.
            </p>
          </HonestStatusBanner>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href={buildHref("dk")}
            className={
              site === "dk"
                ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            DraftKings
          </Link>
          <Link
            href={buildHref("fd")}
            className={
              site === "fd"
                ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            FanDuel
          </Link>
          <Link
            href="/pro/nfl/weekly-fantasy"
            className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70 hover:border-kos-gold/30"
          >
            Weekly Fantasy →
          </Link>
        </div>
      </section>

      <section className="mt-6 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">Top projections</h2>
          <ol className="mt-3 space-y-2">
            {topProj.map((r, i) => (
              <li
                key={r.playerKey}
                className="flex justify-between gap-2 text-sm"
              >
                <span>
                  {i + 1}. {r.playerName}{" "}
                  <span className="text-kos-text/50">
                    {r.position} · {r.team}
                  </span>
                </span>
                <span className="font-semibold text-kos-text">
                  {r.proj.toFixed(1)}
                </span>
              </li>
            ))}
          </ol>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">Best value</h2>
          <p className="mt-3 text-sm text-kos-text/60">
            Value (proj / salary) populates when {site === "dk" ? "DK" : "FD"}{" "}
            salary feeds join. Projection leaders are ready above.
          </p>
        </div>
      </section>

      <section className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
        {/* Opp / Salary / Value / Own% columns hidden until slate feeds join. */}
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/60">
              <th className="px-3 py-3">Player</th>
              <th className="px-3 py-3">Pos</th>
              <th className="px-3 py-3">Team</th>
              <th className="px-3 py-3">Proj</th>
              <th className="px-3 py-3">Ceiling</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 120).map((r) => (
              <tr
                key={r.playerKey}
                className="border-b border-white/5 odd:bg-white/[0.02]"
              >
                <td className="px-3 py-2 font-medium text-kos-text">
                  {r.playerName}
                </td>
                <td className="px-3 py-2 text-kos-text/70">{r.position}</td>
                <td className="px-3 py-2">
                  <Link
                    href={`/pro/nfl/teams/${r.team}/overview`}
                    className="text-kos-gold/90 hover:text-kos-gold"
                  >
                    {r.team}
                  </Link>
                </td>
                <td className="px-3 py-2 font-semibold text-kos-gold">
                  {r.proj.toFixed(1)}
                </td>
                <td className="px-3 py-2 text-kos-text/75">
                  {r.ceiling.toFixed(1)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
