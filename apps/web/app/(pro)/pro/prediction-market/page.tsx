import Link from "next/link";

export default function PredictionMarketPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Link
        href="/pro/welcome"
        className="inline-flex items-center gap-2 text-sm text-kos-gold/90 hover:text-kos-gold mb-6"
      >
        ← Pro
      </Link>
      <h1 className="text-3xl font-semibold text-kos-text">Prediction Market</h1>
      <p className="mt-2 text-kos-text/70">
        Prediction market data and insights. Coming soon.
      </p>
      <div className="mt-8 rounded-xl border border-kos-border bg-kos-surface/40 p-8 text-center text-kos-text/60">
        Prediction market tools and data will be available here.
      </div>
    </main>
  );
}
