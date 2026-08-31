import CfbFuturesCompareTable, {
  type CfbFuturesCompareRow,
} from "@/components/pro/cfb/CfbFuturesCompareTable";
import SportHubShell from "@/components/pro/SportHubShell";
import { cfbTeamDisplayName } from "@/lib/cfb-conferences";
import {
  cfbCfpOddsForTeam,
  cfbConfOddsForTeam,
  cfbNattyOddsForTeam,
  formatCfbImpliedPct,
  formatCfbMarketOdds,
  formatCfbOddsAsOf,
  loadCfbFuturesOdds,
} from "@/lib/cfb-futures-odds";
import {
  cfbKeiVersionStrip,
  loadCfbFuturesPack,
} from "@/lib/cfb-kei-artifacts";

export const dynamic = "force-dynamic";

type SearchValue = string | string[] | undefined;

function firstParam(value: SearchValue): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

function sortRows(
  rows: CfbFuturesCompareRow[],
  byMarket: boolean,
): CfbFuturesCompareRow[] {
  return [...rows].sort((a, b) => {
    if (byMarket) {
      const am = a.market?.impliedPct ?? -1;
      const bm = b.market?.impliedPct ?? -1;
      if (bm !== am) return bm - am;
    }
    const ao = a.ourPct ?? -1;
    const bo = b.ourPct ?? -1;
    return bo - ao;
  });
}

export default async function CfbFuturesPage({
  searchParams,
}: {
  searchParams?:
    | Record<string, SearchValue>
    | Promise<Record<string, SearchValue>>;
}) {
  const params =
    searchParams && typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<Record<string, SearchValue>>)
      : ((searchParams as Record<string, SearchValue>) ?? {});
  const sortMarket = firstParam(params.sort).toLowerCase() === "market";

  const pack = loadCfbFuturesPack();
  const version = cfbKeiVersionStrip();
  const market = await loadCfbFuturesOdds();
  const teams = pack.teams ?? [];
  const confs = Object.entries(pack.conference_titles ?? {}).sort(([a], [b]) =>
    a.localeCompare(b),
  );

  const nattyRows = sortRows(
    teams.slice(0, 40).map((row) => ({
      team: row.team,
      conference: row.conference,
      ourPct: row.natty_pct,
      market: cfbNattyOddsForTeam(market, row.team),
    })),
    sortMarket,
  );
  const cfpRows = sortRows(
    [...teams]
      .sort((a, b) => (b.cfp_make_pct ?? 0) - (a.cfp_make_pct ?? 0))
      .slice(0, 40)
      .map((row) => ({
        team: row.team,
        conference: row.conference,
        ourPct: row.cfp_make_pct,
        market: cfbCfpOddsForTeam(market, row.team),
      })),
    false,
  );

  const nattyMatched = nattyRows.filter((r) => r.market).length;
  const cfpMatched = cfpRows.filter((r) => r.market).length;
  const confShown = confs.reduce((n, [, list]) => n + list.slice(0, 6).length, 0);
  const confMatched = confs.reduce(
    (n, [, list]) =>
      n +
      list
        .slice(0, 6)
        .filter((row) => cfbConfOddsForTeam(market, row.team)).length,
    0,
  );

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Futures"
      summary="KosEdge sim next to current book odds. Sim probabilities stay sim-derived. Market is information only — not blended, not a PLAY tag."
      honestyNote="Not advice. Missing book prices show —."
      primaryHref="/pro/cfb/projections"
      primaryLabel="Win totals"
      secondaryHref="/edge-board/cfb?week=1"
      secondaryLabel="Edge Board"
    >
      <section className="rounded-2xl border border-kos-gold/25 bg-black/35 px-4 py-3 text-sm text-kos-text/80">
        <p className="font-semibold text-kos-gold">
          Methods · 12-team CFP · N={version.n_sims} · {version.futures_version}
        </p>
        <p className="mt-1 text-xs leading-relaxed text-kos-text/70">
          Sim-derived probabilities from season paths. Engine{" "}
          {version.engine_version} · sim as_of {version.as_of} ·
          used_in_spread=false. Market odds from {market.source} (
          {market.sportKey}), updated {formatCfbOddsAsOf(market.asOfUtc)}. Best
          American among configured books. Implied % is raw (juice in), not
          no-vig. Not advice.
        </p>
        <p className="mt-2 text-xs leading-relaxed text-kos-text/60">
          {market.note} {market.cfpNote} {market.confNote}
        </p>
      </section>

      <CfbFuturesCompareTable
        caption="National Championship"
        ourLabel="KosEdge sim Natty %"
        rows={nattyRows}
        matched={nattyMatched}
        sortIsMarket={sortMarket}
        sortSimHref="/pro/cfb/futures"
        sortMarketHref="/pro/cfb/futures?sort=market"
      />

      <CfbFuturesCompareTable
        caption="CFP / Playoff make"
        ourLabel="KosEdge sim CFP %"
        rows={cfpRows}
        matched={cfpMatched}
      />

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-kos-text">
          Conference titles
        </h2>
        <p className="mt-0.5 text-xs text-kos-text/55">
          Market matched {confMatched}/{confShown} shown
        </p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {confs.map(([conf, list]) => (
            <div
              key={conf}
              className="rounded-xl border border-white/10 bg-black/30 px-4 py-3"
            >
              <p className="text-sm font-semibold text-kos-gold">{conf}</p>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-left text-xs text-kos-text/80">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-[0.12em] text-kos-text/45">
                      <th className="py-1 pr-2">Team</th>
                      <th className="py-1 pr-2">KosEdge sim</th>
                      <th className="py-1 pr-2">Market</th>
                      <th className="py-1">Implied</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.slice(0, 6).map((row) => {
                      const snap = cfbConfOddsForTeam(market, row.team);
                      return (
                        <tr key={row.team}>
                          <td className="py-1 pr-2 font-medium text-kos-text">
                            {cfbTeamDisplayName(row.team)}
                          </td>
                          <td className="py-1 pr-2 tabular-nums text-kos-gold">
                            {row.conf_title_pct}
                          </td>
                          <td className="py-1 pr-2 tabular-nums">
                            {formatCfbMarketOdds(snap)}
                          </td>
                          <td className="py-1 tabular-nums">
                            {formatCfbImpliedPct(snap)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </section>
    </SportHubShell>
  );
}
