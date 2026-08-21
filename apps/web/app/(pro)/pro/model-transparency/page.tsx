import type { Metadata } from "next";
import Link from "next/link";
import NflProShell from "@/components/pro/nfl/NflProShell";
import {
  MODEL_TRANSPARENCY_CONTRACT,
  MODEL_TRANSPARENCY_DONT,
  MODEL_TRANSPARENCY_FOOTER_LINKS,
  MODEL_TRANSPARENCY_GLOSSARY,
  MODEL_TRANSPARENCY_ONE_LINER,
  MODEL_TRANSPARENCY_SHOW,
  MODEL_TRANSPARENCY_TITLE,
} from "@/lib/model-transparency-hub";
import {
  loadNflVegasBenchmarkReport,
  percentBetter,
} from "@/lib/nfl-vegas-benchmark";

export const metadata: Metadata = {
  title: MODEL_TRANSPARENCY_TITLE,
  description: MODEL_TRANSPARENCY_ONE_LINER,
};

function StatCard({
  label,
  model,
  market,
  unit,
  lowerIsBetter = true,
}: {
  label: string;
  model: number;
  market: number;
  unit: string;
  lowerIsBetter?: boolean;
}) {
  const better = lowerIsBetter ? model < market : model > market;
  const pct = percentBetter(model, market);
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
          {market.toFixed(unit === "brier" ? 4 : 3)}
        </span>
        <span className="text-xs text-kos-text/50">consensus close</span>
      </div>
      <div
        className={`mt-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
          better
            ? "bg-edge-green/10 text-edge-green border border-edge-green/30"
            : "bg-white/5 text-kos-text/60 border border-white/10"
        }`}
      >
        {better
          ? `${Math.abs(pct).toFixed(1)}% better than market`
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
          <Link
            href="#glossary"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Surface guide
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
                applied unchanged to {report.methodology.testSampleSize} games
                in 2025. This is the honest test: performance on games the
                tuning process never saw.
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-3">
                <StatCard
                  label="Spread error (MAE, points)"
                  model={report.results2025Holdout.spreadMae.model}
                  market={report.results2025Holdout.spreadMae.vegas}
                  unit="points"
                />
                <StatCard
                  label="Total error (MAE, points)"
                  model={report.results2025Holdout.totalMae.model}
                  market={report.results2025Holdout.totalMae.vegas}
                  unit="points"
                />
                <StatCard
                  label="Win probability calibration (Brier)"
                  model={
                    report.results2025Holdout.winProbabilityBrier.model
                  }
                  market={
                    report.results2025Holdout.winProbabilityBrier.vegas
                  }
                  unit="brier"
                />
              </div>
              <div className="mt-4 rounded-xl border border-kos-border bg-kos-surface/40 p-5">
                <div className="text-sm text-kos-text/70">
                  Statistical significance (spread, paired bootstrap, 5,000
                  resamples)
                </div>
                <div className="mt-2 text-kos-text">
                  Model beats the market by{" "}
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
                {report.resultsFull13YrSample.sampleSize.toLocaleString()}{" "}
                games)
              </h2>
              <p className="mt-1 text-sm text-kos-text/60">
                {report.resultsFull13YrSample.note}
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <StatCard
                  label="Spread error (MAE, points)"
                  model={report.resultsFull13YrSample.spreadMae.model}
                  market={report.resultsFull13YrSample.spreadMae.vegas}
                  unit="points"
                />
                <StatCard
                  label="Total error (MAE, points)"
                  model={report.resultsFull13YrSample.totalMae.model}
                  market={report.resultsFull13YrSample.totalMae.vegas}
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
            Backtest report not found. Run the NFL blend-weight tune script to
            regenerate the held-out market benchmark report.
          </p>
        )}

        <section className="mt-10 border-t border-white/10 pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-text/60">
            Other sports &amp; live tracking
          </h2>
          <p className="mt-2 text-sm text-kos-text/60">
            Live closing-line-value tracking (open vs. close) lives on{" "}
            <Link
              href="/pro/clv-tracker"
              className="font-medium text-kos-gold/80 hover:text-kos-gold hover:underline"
            >
              CLV Tracker
            </Link>
            . It is a live sample as the season plays out — not a substitute
            for the held-out check above.
          </p>
        </section>

        <section
          className="mt-12 border-t border-white/10 pt-10"
          aria-labelledby="core-contract"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
            Product map
          </p>
          <h2
            id="core-contract"
            className="mt-2 text-xl font-semibold text-kos-gold"
          >
            Core contract
          </h2>
          <p className="mt-2 text-sm text-kos-text/60">
            {MODEL_TRANSPARENCY_ONE_LINER}.
          </p>
          <dl className="mt-4 space-y-4">
            {MODEL_TRANSPARENCY_CONTRACT.map((row) => (
              <div
                key={row.term}
                className="rounded-xl border border-white/10 bg-black/25 px-4 py-3"
              >
                <dt className="text-sm font-semibold text-kos-text">
                  {row.term}
                </dt>
                <dd className="mt-1 text-sm leading-relaxed text-kos-text/70">
                  {row.meaning}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="mt-10" aria-labelledby="show-vs-dont">
          <h2
            id="show-vs-dont"
            className="text-xl font-semibold text-kos-gold"
          >
            What we show vs what we don&apos;t
          </h2>
          <p className="mt-3 text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/45">
            We show
          </p>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-relaxed text-kos-text/75">
            {MODEL_TRANSPARENCY_SHOW.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="mt-5 text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/45">
            We don&apos;t
          </p>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-relaxed text-kos-text/75">
            {MODEL_TRANSPARENCY_DONT.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>

        <section
          id="glossary"
          className="mt-10 scroll-mt-28"
          aria-labelledby="glossary-heading"
        >
          <h2
            id="glossary-heading"
            className="text-xl font-semibold text-kos-gold"
          >
            Surface guide
          </h2>
          <p className="mt-2 text-sm text-kos-text/60">
            What each board is — and is not. Jump:
          </p>
          <nav
            aria-label="Surface glossary"
            className="mt-3 flex flex-wrap gap-2"
          >
            {MODEL_TRANSPARENCY_GLOSSARY.map((entry) => (
              <a
                key={entry.id}
                href={`#${entry.id}`}
                className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs font-medium text-kos-text/80 hover:border-kos-gold/40 hover:text-kos-gold"
              >
                {entry.title}
              </a>
            ))}
          </nav>
          <div className="mt-6 space-y-5">
            {MODEL_TRANSPARENCY_GLOSSARY.map((entry) => (
              <article
                key={entry.id}
                id={entry.id}
                className="scroll-mt-28 rounded-xl border border-white/10 bg-black/25 px-4 py-4"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="text-base font-semibold text-kos-text">
                    {entry.title}
                  </h3>
                  {entry.href ? (
                    <Link
                      href={entry.href}
                      className="text-xs font-medium text-kos-gold/80 hover:text-kos-gold hover:underline"
                    >
                      Open →
                    </Link>
                  ) : null}
                </div>
                <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-kos-text/70">
                  {entry.lines.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <footer className="mt-10 border-t border-white/10 pt-6">
          <nav
            aria-label="Related"
            className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-kos-text/60"
          >
            {MODEL_TRANSPARENCY_FOOTER_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="hover:text-kos-gold"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </footer>
      </main>
    </NflProShell>
  );
}
