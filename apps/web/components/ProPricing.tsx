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

const free: Plan = {
  title: "Free",
  price: "$0",
  cadence: "",
  sub: "Public Edge Board, odds comparison, free Insights Doctrine, and limited weekly notes. No card required.",
  badge: "Start Here",
  cta: "Go to Hub",
};

const weekly: Plan = {
  title: "Weekly",
  price: "$5.99",
  cadence: "per week",
  sub: "Full Pro desk for a short look. Cancel anytime.",
  badge: "Check Us Out",
  cta: "Explore Pro",
};

const monthly: Plan = {
  title: "Monthly",
  price: "$12.99",
  cadence: "per month",
  sub: "Most popular for the ongoing season desk.",
  highlight: true,
  badge: "Most Popular",
  cta: "Explore Pro",
};

const yearly: Plan = {
  title: "Yearly",
  price: "$116.91",
  cadence: "per year",
  sub: "Best long-term rate for a full season process.",
  badge: "Best Value",
  cta: "Explore Pro",
};

const FREE_FEATURES = [
  "Multi-sport Edge Board (public slate)",
  "Odds comparison",
  "Insights Doctrine (house rules)",
  "Limited weekly Insights teasers",
  "About / Methodology / public hub access",
];

const PRO_FEATURES = [
  "Multi-sport Edge Boards with KEI / Edge / tags",
  "Model vs KEI where live",
  "NFL season engine, game boxes, and survivor tools",
  "Fantasy draft desk + mocks",
  "CFB project-game / model views",
  "Full Insights — weekly desk notes + archive",
  "Sport hubs, power ratings, and deeper Pro tools",
];

function goToUpgradeFlow(planTitle: string, openAccessPreview: boolean) {
  if (openAccessPreview || planTitle === "Free") {
    window.location.href = "/pro/welcome";
    return;
  }
  // Until checkout is fully launched, route paid-plan users through signup/pricing.
  window.location.href = "/auth/signup?callbackUrl=/pricing";
}

export default function ProPricing({
  openAccessPreview = false,
}: {
  openAccessPreview?: boolean;
}) {
  const labelForPlan = (plan: Plan): string => {
    if (!openAccessPreview) {
      return plan.title === "Free" ? "Go to Hub" : plan.cta;
    }
    return plan.title === "Free" ? "Go to Hub" : "Explore Pro";
  };

  return (
    <section className="w-full">
      <div className="text-center">
        <div className="text-sm text-gray-400">KosEdge Pricing</div>
        <h2 className="mt-2 text-4xl sm:text-5xl font-bebas tracking-tight text-kos-gold">
          Free desk access. Pro for the full board.
        </h2>
        <p className="mt-3 text-sm sm:text-base text-gray-200/80 max-w-3xl mx-auto leading-7">
          KosEdge is a multi-sport analytics and handicapping desk — Model, KEI,
          and Edge. Free gets you into the public board and Doctrine. Pro
          unlocks the live desk: KEI lines, tags, season tools, fantasy, and
          full Insights.
        </p>
        <p className="mt-2 text-sm text-gray-400">
          No pick-selling. Process over vibes. Cancel anytime.
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="rounded-3xl border border-white/12 bg-black/30 backdrop-blur-xl p-6 sm:p-7">
          <h3 className="text-lg font-semibold text-kos-text">Free</h3>
          <p className="mt-2 text-sm text-gray-300/80 leading-6">
            Start on the public surfaces. Learn how the desk thinks before you
            upgrade.
          </p>
          <ul className="mt-4 space-y-2 text-sm text-gray-200/85">
            {FREE_FEATURES.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-kos-gold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-3xl border border-kos-gold/35 bg-kos-gold/5 backdrop-blur-xl p-6 sm:p-7">
          <h3 className="text-lg font-semibold text-kos-gold">Pro</h3>
          <p className="mt-2 text-sm text-gray-200/85 leading-6">
            The full handicapping desk — numbers, tools, and ongoing notes that
            match how KosEdge actually works.
          </p>
          <ul className="mt-4 space-y-2 text-sm text-gray-100/90">
            {PRO_FEATURES.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-kos-gold shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-5">
        {[free, weekly, monthly].map((p) => (
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
              {p.cadence && (
                <div className="pb-2 text-sm text-gray-400">{p.cadence}</div>
              )}
            </div>

            {p.sub && (
              <div className="mt-2 text-sm text-gray-300/80 leading-6">
                {p.sub}
              </div>
            )}

            <button
              type="button"
              className={[
                "mt-6 w-full px-4 py-3 rounded-2xl font-semibold transition",
                p.highlight
                  ? "bg-kos-gold text-black hover:brightness-110 shadow-lg shadow-kos-gold/25"
                  : "bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10",
              ].join(" ")}
              onClick={() => goToUpgradeFlow(p.title, openAccessPreview)}
            >
              {labelForPlan(p)}
            </button>
            {p.title === "Free" && (
              <p className="mt-2 text-xs text-gray-500">
                Explore the public desk before you upgrade.
              </p>
            )}

            <div className="mt-3 text-xs text-gray-500">
              {p.title === "Free"
                ? "No card required"
                : "Cancel anytime • Instant access"}
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
                onClick={() => goToUpgradeFlow(yearly.title, openAccessPreview)}
              >
                {labelForPlan(yearly)}
              </button>

              <div className="mt-3 text-xs text-gray-500 text-center">
                Lowest effective rate • Built for long-term edge
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-xs text-gray-500">
        <Link href="/methodology" className="hover:text-gray-300 transition">
          View methodology
        </Link>
        <span className="opacity-40">•</span>
        <Link href="/edge-board" className="hover:text-gray-300 transition">
          See sample Edge Board
        </Link>
        <span className="opacity-40">•</span>
        <Link
          href="/insights/doctrine"
          className="hover:text-gray-300 transition"
        >
          Insights Doctrine
        </Link>
      </div>
    </section>
  );
}
