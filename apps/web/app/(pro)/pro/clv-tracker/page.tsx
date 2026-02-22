import Link from "next/link";

export default function CLVTrackerPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Link
        href="/pro/welcome"
        className="inline-flex items-center gap-2 text-sm text-kos-gold/90 hover:text-kos-gold mb-6"
      >
        ← Pro
      </Link>
      <h1 className="text-3xl font-semibold text-kos-text">CLV Tracker</h1>
      <p className="mt-2 text-kos-text/70">
        Closing Line Value tracking: % of plays with positive EV at close, avg
        edge open vs close, distribution.
      </p>
      <div className="mt-8 space-y-6">
        <div className="rounded-xl border border-kos-border bg-kos-surface/40 p-5">
          <div className="text-sm text-kos-text/70">
            % of plays with positive EV at close
          </div>
          <div className="mt-1 text-2xl font-semibold text-kos-text">—</div>
        </div>
        <div className="rounded-xl border border-kos-border bg-kos-surface/40 p-5">
          <div className="text-sm text-kos-text/70">
            Avg Edge at Open vs Close
          </div>
          <div className="mt-1 text-2xl font-semibold text-kos-text">—</div>
        </div>
        <div className="rounded-xl border border-kos-border bg-kos-surface/40 p-5">
          <div className="text-sm text-kos-text/70">Distribution chart</div>
          <div className="mt-4 h-48 flex items-center justify-center rounded-lg bg-kos-black/50 text-kos-text/50 text-sm">
            Chart placeholder
          </div>
        </div>
      </div>
      <p className="mt-6 text-sm text-kos-text/60">
        Coming soon. Data will populate as tracking rolls out.
      </p>
    </main>
  );
}
