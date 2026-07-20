import Link from "next/link";
import {
  formatPercent,
  formatSigned,
  situationBucketLabel,
  type NflQbSituationalSplitRow,
  type NflTeamDirectionTendencyRow,
  type NflTeamSituationalTendencyRow,
  type TendencyPerspective,
} from "@/lib/nfl-tendencies";

export type SituationTabKey = "down_distance" | "score_state" | "field_position";

const SITUATION_TABS: Array<{ key: SituationTabKey; label: string }> = [
  { key: "down_distance", label: "Down & Distance" },
  { key: "score_state", label: "Score State" },
  { key: "field_position", label: "Field Position" },
];

const QB_SITUATION_TABS: Array<{ key: string; label: string }> = [
  { key: "down_type", label: "Down Type" },
  { key: "pressure", label: "Pressure vs. Clean" },
  { key: "score_state", label: "Score State" },
  { key: "field_position", label: "Field Position" },
];

function buildHref(params: {
  team: string;
  season?: number;
  week?: number;
  perspective: TendencyPerspective;
  situation: SituationTabKey;
  qbSituation?: string;
}): string {
  const url = new URLSearchParams();
  if (params.season) url.set("season", String(params.season));
  if (params.week) url.set("week", String(params.week));
  url.set("perspective", params.perspective);
  url.set("situation", params.situation);
  if (params.qbSituation) url.set("qbSituation", params.qbSituation);
  return `/pro/nfl/teams/${params.team}/tendencies?${url.toString()}`;
}

export default function TeamTendencyPanels({
  team,
  season,
  requestedSeason,
  usedFallback,
  filters,
  perspective,
  activeSituation,
  activeQbSituation,
  situational,
  direction,
  qbSplits,
}: {
  team: string;
  season: number;
  requestedSeason: number;
  usedFallback: boolean;
  filters: { season?: number; week?: number };
  perspective: TendencyPerspective;
  activeSituation: SituationTabKey;
  activeQbSituation: string;
  situational: NflTeamSituationalTendencyRow[];
  direction: NflTeamDirectionTendencyRow | null;
  qbSplits: NflQbSituationalSplitRow[];
}) {
  const filteredSituational = situational.filter((row) => row.situationType === activeSituation);
  const groupedQbSplits = new Map<string, NflQbSituationalSplitRow[]>();
  for (const row of qbSplits) {
    if (row.situationType !== activeQbSituation) continue;
    const key = `${row.playerId}-${row.playerName}`;
    const existing = groupedQbSplits.get(key) ?? [];
    existing.push(row);
    groupedQbSplits.set(key, existing);
  }

  return (
    <div className="space-y-5">
      {usedFallback ? (
        <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-100">
          No real play-by-play exists yet for {requestedSeason} — showing the most recent completed season with real
          tendency data ({season}) instead.
        </div>
      ) : null}

      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-kos-text">Situational Tendencies</h3>
            <p className="mt-1 text-sm text-kos-text/70">
              Real down/distance, score-state, and field-position splits from play-by-play — pass/run mix, pace, and
              efficiency in each situation. Not coverage-scheme labels (those don&apos;t exist in free data).
            </p>
          </div>
          <nav className="flex gap-2" aria-label="Perspective">
            {(["offense", "defense"] as TendencyPerspective[]).map((p) => (
              <Link
                key={p}
                href={buildHref({ team, season: filters.season, week: filters.week, perspective: p, situation: activeSituation, qbSituation: activeQbSituation })}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold capitalize transition ${
                  perspective === p
                    ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                    : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25"
                }`}
              >
                {p === "offense" ? "Offense" : "Defense allows"}
              </Link>
            ))}
          </nav>
        </div>

        <nav className="mt-4 flex flex-wrap gap-2" aria-label="Situation type">
          {SITUATION_TABS.map((tab) => (
            <Link
              key={tab.key}
              href={buildHref({ team, season: filters.season, week: filters.week, perspective, situation: tab.key, qbSituation: activeQbSituation })}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                activeSituation === tab.key
                  ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                  : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-edge-green/25"
              }`}
            >
              {tab.label}
            </Link>
          ))}
        </nav>

        {filteredSituational.length === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-kos-text/70">
            No situational tendency rows for this team/season/perspective yet.
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0">
              <thead>
                <tr>
                  {["Situation", "Plays", "Pass Rate", "PROE", "Shotgun", "No-Huddle", "EPA/Play", "Success", "Explosive", "Sack"].map(
                    (label) => (
                      <th
                        key={label}
                        className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65"
                      >
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {filteredSituational.map((row) => (
                  <tr key={row.situationBucket} className="odd:bg-white/3">
                    <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-text">
                      {situationBucketLabel(row.situationBucket)}
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">{row.plays}</td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-gold">{formatPercent(row.passRate)}</td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                      {formatSigned(row.passRateOverExpected * 100, 1)}pp
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">{formatPercent(row.shotgunRate)}</td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">{formatPercent(row.noHuddleRate)}</td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">{formatSigned(row.epaPerPlay)}</td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">{formatPercent(row.successRate)}</td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                      {formatPercent(row.explosivePlayRate)}
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">{formatPercent(row.sackRate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <h3 className="text-lg font-semibold text-kos-text">Pass Direction</h3>
          <p className="mt-1 text-sm text-kos-text/70">
            Real left/middle/right target-location mix for {perspective === "offense" ? "this team's offense" : "what this defense allows"}.
          </p>
          {direction ? (
            <div className="mt-4 grid grid-cols-3 gap-2">
              <DirectionStat label="Left" value={direction.passLeftRate} />
              <DirectionStat label="Middle" value={direction.passMiddleRate} />
              <DirectionStat label="Right" value={direction.passRightRate} />
            </div>
          ) : (
            <p className="mt-4 text-sm text-kos-text/60">No direction data available.</p>
          )}
        </article>

        <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <h3 className="text-lg font-semibold text-kos-text">Run Direction &amp; Gap</h3>
          <p className="mt-1 text-sm text-kos-text/70">Real left/middle/right and end/guard/tackle gap mix on rush attempts.</p>
          {direction ? (
            <div className="mt-4 grid grid-cols-3 gap-2">
              <DirectionStat label="Left" value={direction.runLeftRate} />
              <DirectionStat label="Middle" value={direction.runMiddleRate} />
              <DirectionStat label="Right" value={direction.runRightRate} />
              <DirectionStat label="End" value={direction.runEndRate} />
              <DirectionStat label="Guard" value={direction.runGuardRate} />
              <DirectionStat label="Tackle" value={direction.runTackleRate} />
            </div>
          ) : (
            <p className="mt-4 text-sm text-kos-text/60">No direction data available.</p>
          )}
        </article>
      </section>

      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-kos-text">QB Situational Splits</h3>
            <p className="mt-1 text-sm text-kos-text/70">
              Real completion%, EPA/play, and CPOE splits for this team&apos;s quarterbacks under pressure vs. clean
              pocket, on early vs. money downs, and by score state.
            </p>
          </div>
          <nav className="flex flex-wrap gap-2" aria-label="QB split type">
            {QB_SITUATION_TABS.map((tab) => (
              <Link
                key={tab.key}
                href={buildHref({ team, season: filters.season, week: filters.week, perspective, situation: activeSituation, qbSituation: tab.key })}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  activeQbSituation === tab.key
                    ? "border border-sky-400/45 bg-sky-400/15 text-sky-300"
                    : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-sky-400/25"
                }`}
              >
                {tab.label}
              </Link>
            ))}
          </nav>
        </div>

        {groupedQbSplits.size === 0 ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-kos-text/70">
            No QB situational split rows for this team/season/split yet.
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            {[...groupedQbSplits.entries()].map(([key, rows]) => (
              <div key={key}>
                <p className="text-sm font-semibold text-kos-text">{rows[0].playerName}</p>
                <div className="mt-2 overflow-x-auto">
                  <table className="min-w-full border-separate border-spacing-0">
                    <thead>
                      <tr>
                        {["Split", "Dropbacks", "Comp%", "YPA", "EPA/Play", "CPOE", "Sack", "INT", "TD"].map((label) => (
                          <th
                            key={label}
                            className="border-b border-white/10 px-3 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-kos-text/60"
                          >
                            {label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.situationBucket} className="odd:bg-white/3">
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm font-semibold text-kos-text">
                            {situationBucketLabel(row.situationBucket)}
                          </td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-text/85">{row.dropbacks}</td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-text/85">
                            {formatPercent(row.completionRate)}
                          </td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-text/85">
                            {row.yardsPerAttempt.toFixed(1)}
                          </td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-gold">{formatSigned(row.epaPerPlay)}</td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-text/85">{formatSigned(row.cpoe, 1)}</td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-text/85">{formatPercent(row.sackRate)}</td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-text/85">
                            {formatPercent(row.interceptionRate)}
                          </td>
                          <td className="border-b border-white/5 px-3 py-1.5 text-sm text-kos-text/85">{formatPercent(row.tdRate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function DirectionStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-2 py-2 text-center">
      <p className="text-[11px] uppercase tracking-wide text-kos-text/60">{label}</p>
      <p className="mt-1 text-base font-semibold text-kos-text">{formatPercent(value)}</p>
    </div>
  );
}
