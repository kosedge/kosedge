import Link from "next/link";
import CfbOfficialSlatePanel from "@/components/pro/cfb/CfbOfficialSlatePanel";
import SportHubShell from "@/components/pro/SportHubShell";
import { parseOfficialSlateWeek } from "@/lib/cfb-official-slate";
import {
  fetchCfbPerformance,
  fetchCfbSeasonEngineStatus,
} from "@/lib/cfb-season-engine";
import { formatIndex } from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";
export const maxDuration = 20;

const TOOLS = [
  {
    href: "/pro/cfb/project-game",
    title: "Project Game",
    body: "Any FBS matchup or Week 0–2 slate row — research-fair spread, total, WP, team totals, σ, and drivers.",
  },
  {
    href: "/pro/cfb/slate",
    title: "Official slate",
    body: "KosEdge W0/W1 artifact — ESPN primary, Odds API fact-check. Open a row in Project Game.",
  },
  {
    href: "/pro/cfb/projections",
    title: "Season projections",
    body: "Research expected wins on the official 889-game slate. CFP / natty omitted.",
  },
  {
    href: "/pro/cfb/teams",
    title: "Power + Teams",
    body: "136 official FBS rows — power, OFF/DEF, QB class, warehouse-fill labels.",
  },
  {
    href: "/pro/cfb/previews",
    title: "Team previews",
    body: "KosEdge house format. Research language. No writer byline.",
  },
  {
    href: "/pro/cfb/conferences",
    title: "Conference previews",
    body: "Power 4 + Notre Dame / Independent note + AAC and Mountain West.",
  },
] as const;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export default async function CfbSeasonModelHubPage({
  searchParams,
}: {
  searchParams?:
    | Promise<Record<string, SearchValue>>
    | Record<string, SearchValue>;
}) {
  const sp =
    searchParams && typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<Record<string, SearchValue>>)
      : ((searchParams as Record<string, SearchValue>) ?? {});
  const week = parseOfficialSlateWeek(firstValue(sp.week));

  const [status, performance] = await Promise.all([
    fetchCfbSeasonEngineStatus(),
    fetchCfbPerformance({ limit: 100 }),
  ]);
  const ladder = status.power_style_ladder?.top ?? [];
  const solid = status.solid_vs_approximate?.solid?.slice(0, 6) ?? [];
  const approx = status.solid_vs_approximate?.approximate?.slice(0, 6) ?? [];
  const deferred =
    status.solid_vs_approximate?.placeholder_or_deferred?.slice(0, 5) ?? [];
  const fidelity = status.team_fidelity_counts;

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Season Model"
      summary="Model is research-fair (used_in_spread=false). KEI is the published line on Edge Board. Tag = KEI vs market."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/project-game"
      primaryLabel="Open Project Game"
      secondaryHref="/edge-board/cfb?week=1"
      secondaryLabel="Edge Board (markets)"
    >
      <section className="mt-6 grid gap-3 sm:grid-cols-2">
        {TOOLS.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="min-h-11 rounded-xl border border-white/10 bg-black/35 px-4 py-4 transition hover:border-kos-gold/40 hover:bg-black/50"
          >
            <h2 className="text-sm font-semibold text-kos-gold">{tool.title}</h2>
            <p className="mt-1.5 text-xs leading-relaxed text-kos-text/70">
              {tool.body}
            </p>
          </Link>
        ))}
        <div className="rounded-xl border border-white/10 bg-black/35 px-4 py-4">
          <h2 className="text-sm font-semibold text-kos-gold">Fidelity</h2>
          <p className="mt-1.5 text-xs leading-relaxed text-kos-text/70">
            KosEdge official slate (ESPN + Odds API fact-check) + 136/136 roster
            overlay. Named ESPN QBs:{" "}
            {fidelity?.espn_named_qb ?? "—"} · warehouse fills labeled on Team
            DNA (not silent 50/50). Returning snap% and portal-out still
            proxies; coaching / HFA curated.
          </p>
        </div>
      </section>

      <CfbOfficialSlatePanel
        week={week}
        hrefForWeek={(w) =>
          w === 0 ? "/pro/cfb/model" : `/pro/cfb/model?week=${w}`
        }
      />

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 px-4 py-4 text-sm text-kos-text/70">
        <p>
          Live engine:{" "}
          <span className="font-semibold text-kos-text">
            {status.engine_version || "unreachable"}
          </span>
          {status.mode ? (
            <span className="text-kos-text/50"> · mode {status.mode}</span>
          ) : null}
          {status.error ? (
            <span className="text-red-300"> — {status.error}</span>
          ) : null}
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              Slate
            </div>
            <div className="mt-0.5 text-kos-text">
              {status.slate_complete ? "complete" : "incomplete"} ·{" "}
              {status.n_games ?? status.schedule_game_count ?? "—"} games
            </div>
          </div>
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              used_in_spread
            </div>
            <div className="mt-0.5 text-kos-text">
              {String(status.used_in_spread ?? false)}
            </div>
          </div>
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              Contract
            </div>
            <div className="mt-0.5 text-kos-text">
              Research fair · KEI is the published line
            </div>
          </div>
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              CFP / natty
            </div>
            <div className="mt-0.5 text-kos-text">omitted (stub)</div>
          </div>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-4 text-xs">
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              Logged
            </div>
            <div className="mt-0.5 text-kos-text">
              {performance.error
                ? "—"
                : `${performance.n_logged ?? 0} · close ${performance.n_with_close ?? 0} · final ${performance.n_with_result ?? 0}`}
            </div>
          </div>
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              ATS / SU
            </div>
            <div className="mt-0.5 text-kos-text">
              {performance.error
                ? "—"
                : `${performance.ats?.record || "0-0"} · SU ${performance.su?.record || "0-0"}`}
            </div>
          </div>
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              Avg CLV
            </div>
            <div className="mt-0.5 text-kos-text">
              {performance.error || performance.clv?.avg_spread_clv == null
                ? "—"
                : `${performance.clv.avg_spread_clv > 0 ? "+" : ""}${performance.clv.avg_spread_clv}`}
            </div>
          </div>
          <div>
            <div className="text-kos-text/45 uppercase tracking-[0.1em]">
              Abs margin err
            </div>
            <div className="mt-0.5 text-kos-text">
              {performance.error ||
              performance.error_metrics?.avg_abs_margin_error == null
                ? "—"
                : performance.error_metrics.avg_abs_margin_error}
            </div>
          </div>
        </div>
        <p className="mt-2 text-xs text-kos-text/50">
          Proxied through Next.js BFF routes — browser never calls Railway with
          secrets. Season simulate stays heavy/API-capped; use Project Game for
          interactive eval. Performance strip reads{" "}
          <code className="text-kos-text/60">/cfb/season-engine/performance</code>
          {performance.error ? (
            <span className="text-kos-text/40">
              {" "}
              (tracking unreachable: {performance.error})
            </span>
          ) : null}
          . In-season efficiency updates (v0.9 foundation) ingest via{" "}
          <code className="text-kos-text/60">/cfb/season-engine/in-season/*</code>
          {" "}— preseason baseline preserved; early weeks move more than late.
        </p>
        {status.schedule_source ? (
          <p className="mt-2 text-xs text-kos-text/50">
            Schedule: {status.schedule_source}
            {status.schedule_game_count != null
              ? ` (${status.schedule_game_count} games)`
              : ""}
            {status.team_count != null ? ` · ${status.team_count} teams` : ""}
          </p>
        ) : null}
        {status.roster_source ? (
          <p className="mt-1 text-xs text-kos-text/50">
            Roster: {status.roster_source}
            {status.depth_source ? ` · depth ${status.depth_source}` : ""}
            {status.portal_source ? ` · portal ${status.portal_source}` : ""}
            {status.as_of || status.roster_as_of
              ? ` · as_of ${status.as_of || status.roster_as_of}`
              : ""}
          </p>
        ) : null}
      </section>

      {ladder.length > 0 ? (
        <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 px-4 py-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold text-kos-gold">
              Power-style ladder (top 20)
            </h2>
            <span className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
              approximate
            </span>
          </div>
          <p className="mt-1 text-xs text-kos-text/55">
            {status.power_style_ladder?.note ??
              "0.5 × (offense_index + defense_index) from packaged compose."}
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[28rem] text-left text-xs text-kos-text/75">
              <thead>
                <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                  <th className="py-2 pr-2">#</th>
                  <th className="py-2 pr-2">Team</th>
                  <th className="py-2 pr-2">Conf</th>
                  <th className="py-2 pr-2">Power</th>
                  <th className="py-2 pr-2">O/D</th>
                  <th className="py-2">Roster</th>
                </tr>
              </thead>
              <tbody>
                {ladder.slice(0, 20).map((row) => (
                  <tr
                    key={row.team}
                    className="border-b border-white/5 last:border-0"
                  >
                    <td className="py-1.5 pr-2 text-kos-text/45">{row.rank}</td>
                    <td className="py-1.5 pr-2 font-medium text-kos-text">
                      {row.team}
                    </td>
                    <td className="py-1.5 pr-2">{row.conference ?? "—"}</td>
                    <td className="py-1.5 pr-2">
                      {formatIndex(row.power_index, 3)}
                    </td>
                    <td className="py-1.5 pr-2">
                      {formatIndex(row.offense_index, 2)}/
                      {formatIndex(row.defense_index, 2)}
                    </td>
                    <td className="py-1.5">
                      {formatIndex(row.roster_strength, 1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="mt-6 grid gap-3 lg:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-black/30 px-4 py-4">
          <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-300/80">
            Can do
          </h3>
          <ul className="mt-2 space-y-1.5 text-xs text-kos-text/70">
            {(solid.length > 0
              ? solid
              : [
                  "Roster / QB / unit composition → project-game",
                  "Variable HFA + coaching week decay",
                  "Early-season uncertainty inspectable",
                ]
            ).map((item) => (
              <li key={item}>· {item}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/30 px-4 py-4">
          <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-amber-200/80">
            Approximate
          </h3>
          <ul className="mt-2 space-y-1.5 text-xs text-kos-text/70">
            {(approx.length > 0
              ? approx
              : [
                  "Packaged roster / QB / unit priors",
                  "Win probs / spreads / totals",
                  "Densified schedule paths",
                ]
            ).map((item) => (
              <li key={item}>· {item}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/30 px-4 py-4">
          <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-kos-text/45">
            Cannot yet
          </h3>
          <ul className="mt-2 space-y-1.5 text-xs text-kos-text/70">
            {(deferred.length > 0
              ? deferred
              : [
                  "Live injury feed (packaged depth as_of only)",
                  "Player box production path",
                ]
            ).map((item) => (
              <li key={item}>· {item}</li>
            ))}
          </ul>
        </div>
      </section>
    </SportHubShell>
  );
}
