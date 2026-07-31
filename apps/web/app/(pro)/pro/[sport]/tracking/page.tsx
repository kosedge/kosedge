import Link from "next/link";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import { env } from "@/lib/config/env";

export const dynamic = "force-dynamic";

type ClvMarketSummary = {
  sample_size?: number;
  avg_clv?: number;
  positive_clv?: number;
  non_positive_clv?: number;
  positive_clv_rate?: number;
};

async function fetchNflClvSummary(): Promise<{
  modelVersion: string;
  lookbackDays: number;
  markets: Record<string, ClvMarketSummary>;
  error?: string;
}> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return {
      modelVersion: "",
      lookbackDays: 0,
      markets: {},
      error: "MODEL_SERVICE_URL is not configured.",
    };
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
      return {
        modelVersion: "",
        lookbackDays: 0,
        markets: {},
        error: `Model service returned ${response.status}.`,
      };
    }
    const payload = (await response.json()) as {
      model_version?: string;
      lookback_days?: number;
      markets?: Record<string, ClvMarketSummary>;
    };
    return {
      modelVersion: String(payload.model_version ?? ""),
      lookbackDays: Number(payload.lookback_days ?? 0),
      markets: payload.markets ?? {},
    };
  } catch {
    return {
      modelVersion: "",
      lookbackDays: 0,
      markets: {},
      error: "Unable to reach CLV summary.",
    };
  } finally {
    clearTimeout(timeout);
  }
}

function pct(value: number | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function num(value: number | undefined, digits = 3): string {
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
    const clv = await fetchNflClvSummary();
    const entries = Object.entries(clv.markets);

    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-semibold text-kos-text">
              NFL Tracking
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-kos-text/70">
              Close-line value and post-close quality review. Outcome-neutral —
              process quality over narrative.
            </p>
            <p className="mt-2 text-xs text-kos-text/55">
              Model {clv.modelVersion || "—"} · lookback {clv.lookbackDays || "—"}{" "}
              days
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`${base}/overview`}
              className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
            >
              Back to Hub
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

        {clv.error ? (
          <div className="mt-6 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
            {clv.error}
          </div>
        ) : null}

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {entries.map(([market, summary]) => (
            <article
              key={market}
              className="rounded-2xl border border-white/10 bg-black/35 p-5"
            >
              <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
                {market}
              </p>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-kos-text/55">Sample</dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {summary.sample_size ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-kos-text/55">Avg CLV</dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {num(summary.avg_clv)}
                  </dd>
                </div>
                <div>
                  <dt className="text-kos-text/55">Positive CLV rate</dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {pct(summary.positive_clv_rate)}
                  </dd>
                </div>
                <div>
                  <dt className="text-kos-text/55">Pos / non-pos</dt>
                  <dd className="mt-1 font-semibold text-kos-text">
                    {summary.positive_clv ?? "—"} /{" "}
                    {summary.non_positive_clv ?? "—"}
                  </dd>
                </div>
              </dl>
            </article>
          ))}
          {entries.length === 0 && !clv.error ? (
            <div className="rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70 md:col-span-2">
              CLV markets will populate as closed tickets accumulate in the
              attribution pipeline.
            </div>
          ) : null}
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-2xl font-semibold text-kos-text">
            {sportName} Tracking
          </h2>
          <p className="mt-2 text-kos-text/70">
            CLV and review dashboards. Outcome-neutral evaluation.
          </p>
        </div>
        <Link
          href={`${base}/overview`}
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          Back to Hub
        </Link>
      </div>
      <div className="mt-8 rounded-2xl border border-kos-border bg-kos-surface/30 p-8">
        <p className="text-kos-text/60">
          Sport tracking is live for NFL via CLV summary. Other leagues follow
          as close-line attribution lands.
        </p>
      </div>
    </main>
  );
}
