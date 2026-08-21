import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import NflTruthStateBadge, {
  NflTruthStateBadges,
} from "@/components/pro/nfl/NflTruthStateBadge";
import { env } from "@/lib/config/env";
import { loadNflClvBenchmarkReport } from "@/lib/nfl-clv-benchmark";
import {
  NFL_CLV_BEAT_CLOSE_HINT,
  NFL_CLV_BEAT_CLOSE_LABEL,
  NFL_CLV_DEFINITION,
  NFL_CLV_LIVE_INCOMPLETE_NOTE,
  NFL_CLV_POPULATION,
  NFL_CLV_TIMESTAMPS,
  formatClvRate,
  liveClvHeroAllowed,
  type LiveClvTrust,
} from "@/lib/nfl-clv-semantics";
import { NFL_PRODUCT_SEASON, resolveNflTruthLabel } from "@/lib/nfl-truth-label";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

export const dynamic = "force-dynamic";

type ClvMarketSummary = {
  sample_size?: number;
  n?: number;
  avg_clv?: number | null;
  beat_close?: number;
  push?: number;
  lose_close?: number;
  decided_n?: number;
  beat_close_rate?: number | null;
  positive_clv?: number;
  non_positive_clv?: number;
  positive_clv_rate?: number | null;
};

type ClvSummaryPayload = {
  modelVersion: string;
  lookbackDays: number;
  definition?: string;
  population?: string;
  timestamps?: string;
  markets: Record<string, ClvMarketSummary>;
  trust: LiveClvTrust | null;
  error?: string;
};

async function fetchNflClvSummary(): Promise<ClvSummaryPayload> {
  const empty: ClvSummaryPayload = {
    modelVersion: "",
    lookbackDays: 0,
    markets: {},
    trust: null,
  };
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return { ...empty, error: "MODEL_SERVICE_URL is not configured." };
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(
      `${base.replace(/\/+$/, "")}/nfl/clv-summary`,
      {
        cache: "no-store",
        signal: controller.signal,
        headers: {
          accept: "application/json",
          ...(env.INTERNAL_API_SECRET
            ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
            : {}),
        },
      },
    );
    if (!response.ok) {
      return { ...empty, error: `Model service returned ${response.status}.` };
    }
    const payload = (await response.json()) as {
      model_version?: string;
      lookback_days?: number;
      definition?: string;
      population?: string;
      timestamps?: string;
      markets?: Record<string, ClvMarketSummary>;
      trust?: LiveClvTrust;
    };
    return {
      modelVersion: String(payload.model_version ?? ""),
      lookbackDays: Number(payload.lookback_days ?? 0),
      definition: payload.definition,
      population: payload.population,
      timestamps: payload.timestamps,
      markets: payload.markets ?? {},
      trust: payload.trust ?? null,
    };
  } catch {
    return { ...empty, error: "Unable to reach CLV summary." };
  } finally {
    clearTimeout(timeout);
  }
}

function num(value: number | null | undefined, digits = 3): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

export default async function TrackingPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;

  if (sportKey === "nfl") {
    const [clv, report] = await Promise.all([
      fetchNflClvSummary(),
      Promise.resolve(loadNflClvBenchmarkReport()),
    ]);
    const entries = Object.entries(clv.markets);
    const truth = resolveNflTruthLabel({
      season: NFL_PRODUCT_SEASON,
      isModelSurface: true,
    });
    const showHeroRate = liveClvHeroAllowed(clv.trust);
    const liveIncomplete =
      !showHeroRate ||
      truth.ui_state === "PRESEASON" ||
      truth.ui_state === "MODEL";

    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-3xl font-semibold text-kos-text">
                NFL Tracking
              </h1>
              <NflTruthStateBadges
                states={
                  liveIncomplete
                    ? ["PRESEASON", "MODEL"]
                    : [truth.ui_state]
                }
              />
            </div>
            <p className="mt-2 max-w-3xl text-sm text-kos-text/70">
              {NFL_CLV_DEFINITION}
            </p>
            <p className="mt-2 text-xs text-kos-text/55">
              Model {clv.modelVersion || "—"} · lookback {clv.lookbackDays || "—"}{" "}
              days · {truth.period_line}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`${base}/overview`}
              className="min-h-11 inline-flex items-center rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
            >
              ← NFL Overview
            </Link>
            <Link
              href="/edge-board/nfl"
              className="min-h-11 inline-flex items-center rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
            >
              Edge Board
            </Link>
            <Link
              href="/pro/clv-tracker"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
            >
              Global CLV Tracker
            </Link>
            <Link
              href="/pro/model-transparency"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
            >
              Model Transparency
            </Link>
          </div>
        </div>

        {liveIncomplete ? (
          <div className="mt-6">
            <HonestStatusBanner
              title="PRESEASON / incomplete — not a beat-the-close rate"
              tone="amber"
            >
              <p>{NFL_CLV_LIVE_INCOMPLETE_NOTE}</p>
              <p className="mt-2">{NFL_CLV_POPULATION}</p>
              <p className="mt-2">{NFL_CLV_TIMESTAMPS}</p>
            </HonestStatusBanner>
          </div>
        ) : null}

        {clv.error ? (
          <div className="mt-6 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
            {clv.error}
          </div>
        ) : null}

        <section className="mt-8">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-kos-text">
              Live lookback
            </h2>
            {liveIncomplete ? (
              <span className="rounded-md border border-amber-400/35 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-200">
                incomplete
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-kos-text/60">
            {NFL_CLV_BEAT_CLOSE_HINT} {NFL_CLV_POPULATION}
          </p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {entries.map(([market, summary]) => {
              const n = summary.n ?? summary.sample_size ?? 0;
              const decided = summary.decided_n ?? 0;
              const beat = summary.beat_close ?? summary.positive_clv;
              const push = summary.push;
              const lose = summary.lose_close;
              return (
                <article
                  key={market}
                  className="rounded-2xl border border-white/10 bg-black/35 p-5"
                >
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
                    {market}
                  </p>
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <dt className="text-kos-text/55">n (rows)</dt>
                      <dd className="mt-1 font-semibold text-kos-text">
                        {n || "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-kos-text/55">Avg CLV</dt>
                      <dd className="mt-1 font-semibold text-kos-text">
                        {num(summary.avg_clv)}
                      </dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-kos-text/55">
                        {NFL_CLV_BEAT_CLOSE_LABEL}
                      </dt>
                      <dd className="mt-1 font-semibold text-kos-text">
                        {showHeroRate
                          ? formatClvRate(summary.beat_close_rate, decided)
                          : "—"}
                        <span className="ml-2 text-xs font-normal text-kos-text/50">
                          decided n={decided || "—"}
                        </span>
                      </dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-kos-text/55">Beat / push / lose</dt>
                      <dd className="mt-1 font-semibold text-kos-text">
                        {beat ?? "—"} / {push ?? "—"} / {lose ?? "—"}
                      </dd>
                    </div>
                  </dl>
                </article>
              );
            })}
            {entries.length === 0 && !clv.error ? (
              <div className="rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70 md:col-span-2">
                No live attribution rows in this lookback. Historical completed
                seasons are below — we do not invent a 2026 beat-close rate.
              </div>
            ) : null}
          </div>
        </section>

        {report ? (
          <section className="mt-10">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-kos-gold">
                2024–2025 completed seasons
              </h2>
              <NflTruthStateBadge state="ARCHIVE" />
            </div>
            <p className="mt-1 text-sm text-kos-text/60">
              {report.methodology.clvDefinition} n is plays with genuine edge vs
              open — {report.methodology.excluded}
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {(
                [
                  ["Moneyline", report.resultsCombined.moneyline, "implied win %"],
                  ["Totals", report.resultsCombined.total, "points"],
                ] as const
              ).map(([label, row, unit]) => (
                <article
                  key={label}
                  className="rounded-2xl border border-white/10 bg-black/35 p-5"
                >
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
                    {label}
                  </p>
                  <p className="mt-3 text-2xl font-semibold text-edge-green">
                    {(row.positiveRate * 100).toFixed(1)}%
                    <span className="ml-2 text-sm font-normal text-kos-text/55">
                      beat the close
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-kos-text/60">
                    avg CLV {row.avgClv > 0 ? "+" : ""}
                    {row.avgClv.toFixed(3)} ({unit}) · n = {row.n.toLocaleString()}
                  </p>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </main>
    );
  }

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} tracking`}
      title={`${sportName} Tracking`}
      summary="CLV and post-close quality review. Outcome-neutral evaluation — process quality over narrative."
      primaryHref="/pro/clv-tracker"
      primaryLabel="Global CLV Tracker →"
      secondaryHref="/pro/model-transparency"
      secondaryLabel="Model Transparency →"
    >
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6 sm:p-8">
        <p className="text-sm font-semibold text-kos-gold">
          Sport CLV summary pending
        </p>
        <p className="mt-2 text-sm text-kos-text/70">
          Close-line attribution is live for NFL. {sportName} tracking populates
          here when the league’s closed-ticket pipeline lands — we do not invent
          CLV rates.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/pro/clv-tracker"
            className="min-h-11 inline-flex items-center rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold"
          >
            Global CLV Tracker
          </Link>
          <Link
            href="/pro/model-transparency"
            className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text"
          >
            Model Transparency
          </Link>
        </div>
      </div>
    </SportHubShell>
  );
}
