import Link from "next/link";

export default function ModelTransparencyPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Link
        href="/pro/welcome"
        className="inline-flex items-center gap-2 text-sm text-kos-gold/90 hover:text-kos-gold mb-6"
      >
        ← Pro
      </Link>
      <h1 className="text-3xl font-semibold text-kos-text">Model Transparency Panel</h1>
      <p className="mt-2 text-kos-text/70">
        Model vs open, model vs close, ROI, EV capture %, sport segmented performance, market segmented performance.
      </p>
      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        {[
          { label: "Model vs Open", value: "—", desc: "Projection vs opening line" },
          { label: "Model vs Close", value: "—", desc: "Projection vs closing line" },
          { label: "ROI", value: "—", desc: "Return on investment" },
          { label: "EV Capture %", value: "—", desc: "Expected value realized" },
          { label: "Sport Segmented", value: "—", desc: "Performance by sport" },
          { label: "Market Segmented", value: "—", desc: "Performance by market" },
        ].map((m) => (
          <div
            key={m.label}
            className="rounded-xl border border-kos-border bg-kos-surface/40 p-5"
          >
            <div className="text-sm text-kos-text/70">{m.label}</div>
            <div className="mt-1 text-2xl font-semibold text-kos-text">{m.value}</div>
            <div className="mt-1 text-xs text-kos-text/60">{m.desc}</div>
          </div>
        ))}
      </div>
      <p className="mt-6 text-sm text-kos-text/60">Coming soon. Data will populate as tracking rolls out.</p>
    </main>
  );
}
