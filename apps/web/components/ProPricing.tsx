"use client";

import Link from "next/link";

type Plan = {
  title: string;
  price: string;
  cadence: string;
  sub?: string;
  highlight?: boolean;
  badge?: string;
  cta: string;
};

const weekly: Plan = {
  title: "Weekly",
  price: "$5.99",
  cadence: "per week",
  sub: "Check us out. Full access, short commitment.",
  badge: "Check Us Out",
  cta: "Start Weekly",
};

const monthly: Plan = {
  title: "Monthly",
  price: "$12.99",
  cadence: "per month",
  sub: "Most popular for serious users.",
  highlight: true,
  badge: "Most Popular",
  cta: "Start Monthly",
};

const yearly: Plan = {
  title: "Yearly",
  price: "$116.91",
  cadence: "per year",
  sub: "Best long-term rate. Built for disciplined players.",
  badge: "Best Value",
  cta: "Start Yearly",
};

// Until full launch: all price clicks go to Pro Hub (no checkout yet)
function goToWelcome() {
  window.location.href = "/pro/welcome";
}

export default function ProPricing() {
  return (
    <section className="w-full">
      <div className="text-center">
        <div className="text-sm text-gray-400">Kos Edge Pro</div>
        <h2 className="mt-2 text-4xl sm:text-5xl font-bebas tracking-tight text-kos-gold">
          Build on Data, Driven by Edge
        </h2>
        <p className="mt-3 text-sm sm:text-base text-gray-200/80 max-w-3xl mx-auto">
          Pro unlocks:
          <span className="text-gray-100">
            {" "}
            Edge Boards for all sports
          </span>, <span className="text-gray-100">game breakdowns</span>,{" "}
          <span className="text-gray-100">season & event previews</span>,{" "}
          <span className="text-gray-100">power ratings</span>, and{" "}
          <span className="text-gray-100">props</span>.
          <span className="block mt-2 text-gray-400">
            No pick-selling. Just information you can act on.
          </span>
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-5">
        {[weekly, monthly].map((p) => (
          <div
            key={p.title}
            className={[
              "relative rounded-3xl border backdrop-blur-xl p-6 sm:p-7 transition",
              p.highlight
                ? "bg-black/45 border-kos-gold/40 shadow-lg shadow-kos-gold/20"
                : "bg-black/30 border-white/12",
            ].join(" ")}
          >
            {p.badge && (
              <div
                className={[
                  "absolute -top-3 left-6 rounded-full px-3 py-1 text-xs font-bold shadow-lg",
                  p.highlight
                    ? "bg-kos-gold text-black shadow-kos-gold/30"
                    : "bg-white/10 text-gray-300 border border-white/20",
                ].join(" ")}
              >
                {p.badge}
              </div>
            )}

            <div className="text-sm text-gray-400">{p.title}</div>

            <div className="mt-2 flex items-end gap-2">
              <div className="text-5xl font-bebas tracking-tight text-gray-100">
                {p.price}
              </div>
              <div className="pb-2 text-sm text-gray-400">{p.cadence}</div>
            </div>

            {p.sub && (
              <div className="mt-2 text-sm text-gray-300/80">{p.sub}</div>
            )}

            <button
              type="button"
              className={[
                "mt-6 w-full px-4 py-3 rounded-2xl font-semibold transition",
                p.highlight
                  ? "bg-kos-gold text-black hover:brightness-110 shadow-lg shadow-kos-gold/25"
                  : "bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10",
              ].join(" ")}
              onClick={goToWelcome}
            >
              {p.cta}
            </button>

            <div className="mt-3 text-xs text-gray-500">
              Cancel anytime • Instant access
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6">
        <div className="relative rounded-3xl border bg-black/50 border-kos-gold/50 backdrop-blur-xl p-7 shadow-xl shadow-kos-gold/25">
          <div className="absolute -top-3 left-6 rounded-full bg-kos-gold text-black px-3 py-1 text-xs font-bold shadow-lg shadow-kos-gold/30">
            {yearly.badge}
          </div>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <div className="text-sm text-gray-300/90">{yearly.title}</div>

              <div className="mt-2 flex items-end gap-3">
                <div className="text-6xl font-bebas tracking-tight text-kos-gold">
                  {yearly.price}
                </div>
                <div className="pb-2 text-sm text-gray-400">
                  {yearly.cadence}
                </div>
              </div>

              <div className="mt-2 text-sm text-gray-200/80">{yearly.sub}</div>
            </div>

            <div className="w-full md:w-[320px]">
              <button
                type="button"
                className="w-full px-4 py-3 rounded-2xl font-semibold bg-kos-gold text-black hover:brightness-110 transition shadow-lg shadow-kos-gold/30"
                onClick={goToWelcome}
              >
                {yearly.cta}
              </button>

              <div className="mt-3 text-xs text-gray-500 text-center">
                Lowest effective rate • Built for long-term edge
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-center gap-4 text-xs text-gray-500">
        <Link href="/insights" className="hover:text-gray-300 transition">
          View methodology
        </Link>
        <span className="opacity-40">•</span>
        <Link href="/edge-board" className="hover:text-gray-300 transition">
          See sample Edge Board
        </Link>
      </div>
    </section>
  );
}
