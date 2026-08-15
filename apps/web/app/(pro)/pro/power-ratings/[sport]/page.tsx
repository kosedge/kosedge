import Link from "next/link";
import { redirect } from "next/navigation";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import {
  enrichNflPowerRatingsWithIntel,
  getNflPowerRatingsBoard,
  getPowerRatings,
  type PowerRatingRow,
} from "@/lib/power-ratings";
import { fetchNflIntel } from "@/lib/nfl-intel";
import { PowerRatingsTable } from "./PowerRatingsTable";
import SportProShell from "@/components/pro/SportProShell";
import NflLineageBadge from "@/components/pro/nfl/NflLineageBadge";
import { NflTruthStateBadges } from "@/components/pro/nfl/NflTruthStateBadge";
import { withEngineVersionOverride } from "@/lib/nfl-lineage";
import { resolveActiveNflLineage } from "@/lib/nfl-launch-research";
import { isNflCalendarPreseason, NFL_PRODUCT_SEASON } from "@/lib/nfl-truth-label";

export const dynamic = "force-dynamic";

function formatSigned(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

function formatPoints(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

function NflAtAGlance({
  rows,
  deskMode,
}: {
  rows: PowerRatingRow[];
  deskMode: boolean;
}) {
  const top5 = rows.slice(0, 5);
  const risers = rows
    .filter((r) => (r.weeklyDelta ?? 0) > 0)
    .sort((a, b) => (b.weeklyDelta ?? 0) - (a.weeklyDelta ?? 0))
    .slice(0, 5);
  const fallers = rows
    .filter((r) => (r.weeklyDelta ?? 0) < 0)
    .sort((a, b) => (a.weeklyDelta ?? 0) - (b.weeklyDelta ?? 0))
    .slice(0, 5);

  const card = (
    title: string,
    items: PowerRatingRow[],
    renderMeta: (r: PowerRatingRow) => string,
  ) => (
    <div className="rounded-xl border border-white/10 bg-black/35 p-4">
      <h3 className="text-sm font-semibold text-kos-gold">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-3 text-xs text-kos-text/55">No movement yet.</p>
      ) : (
        <ol className="mt-3 space-y-2">
          {items.map((r) => (
            <li
              key={r.teamNorm ?? r.team}
              className="flex items-baseline justify-between gap-2 text-sm"
            >
              <Link
                href={`/pro/nfl/teams/${r.teamNorm ?? ""}/overview`}
                className="font-medium text-kos-text hover:text-kos-gold"
              >
                {r.rank}. {r.teamNorm ?? r.team}
              </Link>
              <span className="text-xs text-kos-text/60">{renderMeta(r)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );

  const valueOf = (r: PowerRatingRow) =>
    deskMode ? (r.modelPr ?? r.rating) : r.rating;

  return (
    <section className="mt-6 grid gap-3 md:grid-cols-3">
      {card("Top 5", top5, (r) =>
        deskMode
          ? `${formatPoints(valueOf(r))} Model PR`
          : `${r.rating.toFixed(2)} wins`,
      )}
      {card("Biggest Risers", risers, (r) =>
        `Δ ${formatSigned(r.weeklyDelta)}`,
      )}
      {card("Biggest Fallers", fallers, (r) =>
        `Δ ${formatSigned(r.weeklyDelta)}`,
      )}
    </section>
  );
}

function bundleLabel(id: string, opts?: { nTeamSims?: number | null }): string {
  const stamp = id.replace("nfl-preseason-sim-2026-", "");
  const day =
    stamp.length >= 8
      ? `${stamp.slice(0, 4)}-${stamp.slice(4, 6)}-${stamp.slice(6, 8)}`
      : null;
  if (opts?.nTeamSims && opts.nTeamSims >= 50000) {
    return day
      ? `Launch ${opts.nTeamSims.toLocaleString()} · ${day}`
      : `Launch ${opts.nTeamSims.toLocaleString()}`;
  }
  if (day) return `Sim ${day}`;
  return id;
}

const DESK_HEADERS = [
  "Team",
  "Model PR",
  "Ryan Adj",
  "Ryan PR",
  "Market PR",
  "Δ Mkt",
  "Off",
  "Def",
  "ST",
  "Active PR",
  "Unc.",
  "Prev Week",
  "Weekly Δ",
] as const;

export default async function PowerRatingsSportPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey === "cfb") redirect("/pro/cfb/teams");
  const sportName = sportDisplayLabel(sportKey);
  const sp = searchParams ? await searchParams : {};
  const bundleRaw = Array.isArray(sp.bundle) ? sp.bundle[0] : sp.bundle;

  if (sportKey === "nfl") {
    const board = getNflPowerRatingsBoard({ bundleId: bundleRaw });
    const deskMode = board.source === "power_desk";
    const [standings, stats] = await Promise.all([
      fetchNflIntel("standings", {}),
      fetchNflIntel("stats", {}),
    ]);
    // Join on canonicalizeNflTeam so LAR board rows hit nflverse LA intel rows.
    const enriched = enrichNflPowerRatingsWithIntel(
      board.rows,
      standings.rows,
      stats.rows,
    );

    const lineage =
      withEngineVersionOverride(
        board.lineage ?? null,
        board.engineVersion,
      ) ?? resolveActiveNflLineage();

    return (
      <SportProShell
        sport="nfl"
        pageTitle="NFL Power Ratings"
        pageSubtitle={
          deskMode
            ? "Model PR = points better/worse than average on a neutral field (same strength path as Season Model). Ryan Adj defaults to 0."
            : "Desk snapshot pending — showing expected-wins outlook until Tuesday publish lands."
        }
      >
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0 space-y-2">
              <NflTruthStateBadges
                states={
                  isNflCalendarPreseason(NFL_PRODUCT_SEASON) ||
                  board.desk?.phase === "preseason"
                    ? ["PRESEASON", "MODEL"]
                    : ["MODEL"]
                }
              />
              <p className="text-sm text-kos-text/65">
                {deskMode
                  ? `Method ${board.desk?.method ?? "B"} · ${board.desk?.phase ?? "preseason"}`
                  : board.bundleId
                    ? `Active · ${bundleLabel(board.bundleId, { nTeamSims: board.nTeamSims })}`
                    : "No sim bundle found"}
                {board.engineVersion ? ` · ${board.engineVersion}` : ""}
                {board.activeRunId
                  ? ` · run ${board.activeRunId.replace("nfl-preseason-sim-2026-", "")}`
                  : ""}
              </p>
              {lineage ? <NflLineageBadge lineage={lineage} /> : null}
            </div>
            <Link
              href="/pro/nfl/model"
              className="min-h-11 inline-flex items-center rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
            >
              True PR drivers →
            </Link>
          </div>
          <p className="mt-2 text-xs text-kos-text/50">
            {deskMode
              ? "Model PR is immutable on this snapshot. Ryan PR = Model + Adj. Active PR folds current injuries; Game PR stays on Edge Board. Early-season Tuesday updates use Bayesian shrinkage (Week 1–4 heavy prior)."
              : "Expected wins remain the season-outlook board. Continuity, QB premium, SOS outlook, and blend live on the Season Model True PR surface."}
          </p>
          {deskMode && board.desk?.stNote ? (
            <p className="mt-2 text-xs text-kos-text/45">
              ST column: {board.desk.stNote}. Market PR shows — until futures /
              win-total implied powers are wired.
            </p>
          ) : null}

          <NflAtAGlance rows={enriched} deskMode={deskMode} />

          <div className="mt-6 overflow-x-auto rounded-2xl border border-kos-border bg-kos-surface/30">
            {deskMode ? (
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-kos-border bg-kos-surface/50">
                    {DESK_HEADERS.map((h) => (
                      <th
                        key={h}
                        className="whitespace-nowrap px-2.5 py-3 text-xs font-semibold uppercase tracking-wide text-kos-text/70"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {enriched.map((r) => (
                    <tr
                      key={r.teamNorm ?? r.team}
                      className="border-b border-kos-border/40 hover:bg-kos-surface/40"
                    >
                      <td className="whitespace-nowrap px-2.5 py-2.5 font-medium">
                        <Link
                          href={`/pro/nfl/teams/${r.teamNorm}/overview`}
                          className="text-kos-text hover:text-kos-gold"
                        >
                          {r.teamNorm}
                        </Link>
                      </td>
                      <td className="px-2.5 py-2.5 font-semibold text-kos-gold">
                        {formatPoints(r.modelPr)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatPoints(r.ryanAdj ?? 0)}
                      </td>
                      <td className="px-2.5 py-2.5 font-medium text-kos-text">
                        {formatPoints(r.ryanPr)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatPoints(r.marketPr)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatSigned(r.deltaMarket)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatPoints(r.offPr)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatPoints(r.defPr)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatPoints(r.stPr)}
                        {r.stApproximate ? (
                          <span className="ml-1 text-[10px] text-kos-text/40">
                            ≈
                          </span>
                        ) : null}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatPoints(r.activePr)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {r.uncertainty != null
                          ? r.uncertainty.toFixed(2)
                          : "—"}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatPoints(r.prevWeekModelPr)}
                      </td>
                      <td className="px-2.5 py-2.5 text-kos-text/75">
                        {formatSigned(r.weeklyDelta)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="min-w-full text-left">
                <thead>
                  <tr className="border-b border-kos-border bg-kos-surface/50">
                    {[
                      "Rank",
                      "Team",
                      "E[Wins]",
                      "Off EPA",
                      "Def EPA",
                      "Weekly Δ",
                      "Rank Δ",
                      "Record",
                    ].map((h) => (
                      <th
                        key={h}
                        className="px-3 py-3 text-xs font-semibold uppercase tracking-wide text-kos-text/70"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {enriched.map((r) => (
                    <tr
                      key={r.teamNorm ?? r.team}
                      className="border-b border-kos-border/40 hover:bg-kos-surface/40"
                    >
                      <td className="px-3 py-2.5 text-sm text-kos-text/80">
                        {r.rank}
                      </td>
                      <td className="px-3 py-2.5 text-sm font-medium">
                        <Link
                          href={`/pro/nfl/teams/${r.teamNorm}/overview`}
                          className="text-kos-text hover:text-kos-gold"
                        >
                          {r.teamNorm}{" "}
                          <span className="text-kos-text/50">{r.team}</span>
                        </Link>
                      </td>
                      <td className="px-3 py-2.5 text-sm font-semibold text-kos-gold">
                        {r.rating.toFixed(2)}
                      </td>
                      <td className="px-3 py-2.5 text-sm text-kos-text/75">
                        {r.offense != null ? r.offense.toFixed(3) : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-sm text-kos-text/75">
                        {r.defense != null ? r.defense.toFixed(3) : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-sm text-kos-text/75">
                        {formatSigned(r.weeklyDelta)}
                      </td>
                      <td className="px-3 py-2.5 text-sm text-kos-text/75">
                        {formatSigned(r.rankDelta, 0)}
                      </td>
                      <td className="px-3 py-2.5 text-sm text-kos-text/75">
                        {r.record ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <p className="mt-3 text-xs text-kos-text/45">
            {deskMode
              ? "Model PR units = points vs league average (neutral field). Ryan Adj policy: ±0.25 routine · ±0.5 meaningful · ±1.0 major · >1.0 needs written reason. Tuesday job: scripts/nfl/tuesday_power_ratings_update.py"
              : "Power Rating fallback = model expected wins. Off/Def = EPA/play (intel)."}
          </p>
        </main>
      </SportProShell>
    );
  }

  const ratings = getPowerRatings(sportKey);

  return (
    <SportProShell
      sport={sportKey}
      pageTitle={`${sportName} Power Ratings`}
      pageSubtitle="Team strength, tiering, and model rankings for slate research. Neutral presentation — not picks."
    >
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <p className="text-sm text-kos-text/65">
            {ratings.length
              ? `${ratings.length} teams ranked`
              : "Ratings feed pending for this sport — shell stays ready without invented numbers."}
          </p>
          <Link
            href="/pro/power-ratings"
            className="min-h-11 inline-flex items-center rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
          >
            All sports
          </Link>
        </div>

        <div className="mt-6">
          <PowerRatingsTable ratings={ratings} sportName={sportName} />
        </div>
      </main>
    </SportProShell>
  );
}
