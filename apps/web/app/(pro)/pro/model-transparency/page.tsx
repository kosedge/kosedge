import Link from "next/link";
import NflProShell from "@/components/pro/nfl/NflProShell";
import {
  loadNflVegasBenchmarkReport,
  percentBetter,
} from "@/lib/nfl-vegas-benchmark";

function StatCard({
  label,
  model,
  vegas,
  unit,
  lowerIsBetter = true,
}: {
  label: string;
  model: number;
  vegas: number;
  unit: string;
  lowerIsBetter?: boolean;
}) {
  const better = lowerIsBetter ? model < vegas : model > vegas;
  const pct = percentBetter(model, vegas);
  return (
    <div className="rounded-xl border border-kos-border bg-kos-surface/40 p-5">
      <div className="text-sm text-kos-text/70">{label}</div>
      <div className="mt-2 flex items-baseline gap-3">
        <span className="text-2xl font-semibold text-kos-text">
          {model.toFixed(unit === "brier" ? 4 : 3)}
        </span>
        <span className="text-xs text-kos-text/50">model</span>
      </div>
      <div className="mt-1 flex items-baseline gap-3">
        <span className="text-lg text-kos-text/60">
          {vegas.toFixed(unit === "brier" ? 4 : 3)}
        </span>
        <span className="text-xs text-kos-text/50">Vegas closing line</span>
      </div>
      <div
        className={`mt-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
          better
            ? "bg-edge-green/10 text-edge-green border border-edge-green/30"
            : "bg-white/5 text-kos-text/60 border border-white/10"
        }`}
      >
        {better
          ? `${Math.abs(pct).toFixed(1)}% better than Vegas`
          : "not better on this metric"}
      </div>
    </div>
  );
}

export default function ModelTransparencyPage() {
  const report = loadNflVegasBenchmarkReport();

  return (
    <NflProShell
      pageTitle="Model Health & Governance"
      pageSubtitle="Accountability surface — model transparency, CLV, and performance. We don't ask you to trust the model; we show the backtest."
      actions={
        <>
          <Link
            href="/pro/clv-tracker"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            CLV Tracker
          </Link>
          <Link
            href="/pro/performance/overview"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Performance
          </Link>
        </>
      }
    >
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
      {report ? (
        <>
          <section>
            <h2 className="text-lg font-semibold text-kos-gold">
              NFL — held-out 2025 season (never used to tune the model)
            </h2>
            <p className="mt-1 text-sm text-kos-text/60">
              Blend weights were selected on 2024 games only, then locked and
              applied unchanged to {report.methodology.testSampleSize} games in
              2025. This is the honest test: performance on games the tuning
              process never saw.
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <StatCard
                label="Spread error (MAE, points)"
                model={report.results2025Holdout.spreadMae.model}
                vegas={report.results2025Holdout.spreadMae.vegas}
                unit="points"
              />
              <StatCard
                label="Total error (MAE, points)"
                model={report.results2025Holdout.totalMae.model}
                vegas={report.results2025Holdout.totalMae.vegas}
                unit="points"
              />
              <StatCard
                label="Win probability calibration (Brier)"
                model={report.results2025Holdout.winProbabilityBrier.model}
                vegas={report.results2025Holdout.winProbabilityBrier.vegas}
                unit="brier"
              />
            </div>
            <div className="mt-4 rounded-xl border border-kos-border bg-kos-surface/40 p-5">
              <div className="text-sm text-kos-text/70">
                Statistical significance (spread, paired bootstrap, 5,000
                resamples)
              </div>
              <div className="mt-2 text-kos-text">
                Model beats Vegas by{" "}
                <span className="font-semibold text-edge-green">
                  {Math.abs(
                    report.results2025Holdout.spreadSignificance.diff,
                  ).toFixed(2)}{" "}
                  points
                </span>{" "}
                on average, 95% CI [
                {report.results2025Holdout.spreadSignificance.ci95Low.toFixed(
                  2,
                )}
                ,{" "}
                {report.results2025Holdout.spreadSignificance.ci95High.toFixed(
                  2,
                )}
                ]
                {report.results2025Holdout.spreadSignificance.significant
                  ? " — statistically significant, not noise."
                  : " — within noise at this sample size."}
              </div>
            </div>
          </section>

          <section className="mt-10">
            <h2 className="text-lg font-semibold text-kos-gold">
              Full 13-season sample (2013–2025,{" "}
              {report.resultsFull13YrSample.sampleSize.toLocaleString()} games)
            </h2>
            <p className="mt-1 text-sm text-kos-text/60">
              {report.resultsFull13YrSample.note}
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <StatCard
                label="Spread error (MAE, points)"
                model={report.resultsFull13YrSample.spreadMae.model}
                vegas={report.resultsFull13YrSample.spreadMae.vegas}
                unit="points"
              />
              <StatCard
                label="Total error (MAE, points)"
                model={report.resultsFull13YrSample.totalMae.model}
                vegas={report.resultsFull13YrSample.totalMae.vegas}
                unit="points"
              />
            </div>
          </section>

          <section className="mt-10 rounded-xl border border-kos-gold/25 bg-kos-gold/5 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-gold">
              Methodology &amp; honest caveats
            </h2>
            <p className="mt-2 text-sm text-kos-text/75">
              {report.methodology.summary}
            </p>
            <ul className="mt-3 list-disc list-inside space-y-1.5 text-sm text-kos-text/65">
              {report.methodology.caveats.map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-kos-text/45">
              Report generated {report.generatedAt} · model{" "}
              {report.modelVersion} · source:{" "}
              {report.methodology.sourceScripts.join(", ")}
            </p>
          </section>
        </>
      ) : (
        <p className="text-sm text-kos-text/60">
          Backtest report not found. Run scripts/nfl/tune_blend_weights.py to
          generate data/ops/nfl-vegas-benchmark-report.json.
        </p>
      )}

      <section className="mt-10 border-t border-white/10 pt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-text/60">
          Other sports &amp; live tracking
        </h2>
        <p className="mt-2 text-sm text-kos-text/60">
          Live closing-line-value tracking (open vs. close, in real time as the
          season plays out) is being built out now that the odds pipeline is
          fully wired — it will appear here once enough games have accumulated
          real open-to-close data.
        </p>
      </section>
      </main>
    </NflProShell>
  );
}
