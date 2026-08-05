import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { fetchCfbSeasonEngineStatus } from "@/lib/cfb-season-engine";
import { formatIndex } from "@/lib/cfb-season-engine-format";

export const dynamic = "force-dynamic";

const TOOLS = [
  {
    href: "/pro/cfb/project-game",
    title: "Project Game",
    body: "Pick two FBS teams and read a clean market card — spread, total, WP→ML — with scannable Off/Def Eff + roster / QB / unit / HFA / coaching drivers.",
  },
] as const;

export default async function CfbSeasonModelHubPage() {
  const status = await fetchCfbSeasonEngineStatus();
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
      summary="Hierarchical CFB season engine with opponent-adjusted efficiency (2025 SP+ carry), ESPN 2026 real-roster overlay, and historical closing-line calibration — team power-style ranks and project-game matchups. Edge Board stays markets-only; no fake KEI invent."
      badge="CFB hist-cal"
      primaryHref="/pro/cfb/project-game"
      primaryLabel="Open Project Game"
      secondaryHref="/edge-board/cfb"
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
            Final-2025 SP+ efficiency carry drives Off/Def Eff alongside ESPN
            2026 roster / QB / units; densified schedule stays approximate.
            Named ESPN QBs: {fidelity?.espn_named_qb ?? "—"} · approximate
            teams: {fidelity?.approximate_curated ?? "—"} · placeholder FBS:{" "}
            {fidelity?.placeholder_fbs ?? "—"}. Returning snap% and portal-out
            still proxies; coaching / HFA curated.
          </p>
        </div>
      </section>

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
        <p className="mt-2 text-xs text-kos-text/50">
          Proxied through Next.js BFF routes — browser never calls Railway with
          secrets. Season simulate stays heavy/API-capped; use Project Game for
          interactive eval.
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
            {status.depth_source ? ` · depth {status.depth_source}` : ""}
            {status.portal_source ? ` · portal {status.portal_source}` : ""}
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
                  "Official full FBS schedule feed",
                  "Market-grade KEI fair lines",
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
