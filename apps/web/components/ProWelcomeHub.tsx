import Link from "next/link";
import Image from "next/image";
import { SPORTS } from "@/lib/sports";
import { getProInsightOfWeek } from "@/lib/insights/pillars";
import { TOP_EDGE, HIGHLIGHTED_GAMES } from "@/lib/featured-games";
import EdgeBoardPreview from "./EdgeBoardPreview";

type HubCard = {
  title: string;
  desc: string;
  href: string;
  accent?: "gold" | "green";
};

const cards: HubCard[] = [
  { title: "Model Transparency Panel", desc: "Model vs open, model vs close, ROI, EV capture %, sport & market performance.", href: "/pro/model-transparency", accent: "gold" },
  { title: "Market Dashboard", desc: "Totals, spreads, steam, key numbers, movement snapshots.", href: "/pro/market", accent: "green" },
  { title: "Workflow", desc: "Build a card. Save leans. Track CLV. One-click book links (V1).", href: "/pro/workflow", accent: "gold" },
  { title: "Prediction Market", desc: "Prediction market data and insights.", href: "/pro/prediction-market", accent: "green" },
  { title: "CLV Tracker", desc: "% plays with +EV at close, avg edge open vs close, distribution chart.", href: "/pro/clv-tracker", accent: "gold" },
  { title: "Props Center", desc: "Prop analyzer and edge screens (V1+).", href: "/pro/props-center", accent: "green" },
  { title: "Power Ratings", desc: "Team strength, updates, and historical context.", href: "/pro/power-ratings", accent: "gold" },
  { title: "Guides", desc: "Discipline + bankroll + model methodology docs.", href: "/methodology", accent: "green" },
];

export default function ProWelcomeHub() {
  const proInsight = getProInsightOfWeek();

  return (
    <section className="w-full">
      {/* Hero: logo + branding + nav + sport links — no Edge Board */}
      <div className="rounded-3xl border border-white/10 bg-black/30 backdrop-blur-xl p-6 sm:p-7 shadow-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="relative h-16 w-16 sm:h-20 sm:w-20 rounded-full overflow-hidden ring-1 ring-white/10 flex-shrink-0">
              <Image
                src="/brand/kosedge-logo-v2.png"
                alt="Kos Edge Analytics"
                fill
                className="object-cover"
                priority
              />
            </div>
            <div className="leading-none min-w-0">
              <div className="text-2xl sm:text-3xl md:text-4xl font-bebas tracking-wider">
                <span className="text-kos-green">KOS</span>{" "}
                <span className="text-kos-gold">EDGE</span>{" "}
                <span className="text-gray-300">ANALYTICS</span>{" "}
                <span className="text-kos-gold drop-shadow-[0_0_12px_rgba(245,185,66,0.35)]">
                  PRO
                </span>
              </div>
              <div className="text-sm text-gray-400 mt-1">
                Beat the <span className="text-white">Number</span> with real{" "}
                <span className="text-kos-gold">Edge</span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/"
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              Home
            </Link>
          </div>
        </div>
        {/* Sport hubs + boards — keep individual sport links */}
        <div className="mt-6 flex flex-wrap gap-2">
          {SPORTS.map((s) => (
            <Link
              key={s.key}
              href={`/pro/${s.key}`}
              className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 hover:border-kos-gold/35 hover:bg-white/10 transition text-sm font-semibold"
            >
              {s.label} Hub
            </Link>
          ))}
          {SPORTS.map((s) => (
            <Link
              key={`board-${s.key}`}
              href={`/edge-board/${s.key}`}
              className="px-3 py-2 rounded-xl bg-kos-gold/10 border border-kos-gold/30 hover:border-kos-gold/50 text-kos-gold transition text-sm font-semibold"
            >
              {s.label} Board
            </Link>
          ))}
        </div>
      </div>

      {/* Top row: Top Edge (left) + Insight of the Week (right) */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Top Edge — edge board preview + link to article */}
        <div className="rounded-3xl border border-white/10 bg-black/30 backdrop-blur-xl p-6 shadow-xl">
          <h3 className="text-lg font-bebas text-kos-gold tracking-wide">Top Edge</h3>
          <div className="mt-4">
            <EdgeBoardPreview
              row={TOP_EDGE.row}
              articleHref={`/pro/articles/${TOP_EDGE.slug}`}
            />
          </div>
        </div>
        {/* Insight of the Week — Pro insight, rotates weekly */}
        <div className="rounded-3xl border border-white/10 bg-black/30 backdrop-blur-xl p-6 shadow-xl">
          <h3 className="text-lg font-bebas text-kos-gold tracking-wide">Insight of the Week</h3>
          <div className="mt-4 text-sm text-gray-200/90 line-clamp-4">
            {proInsight ? (
              <>
                <p className="font-medium text-kos-gold">{proInsight.title}</p>
                {proInsight.body.slice(0, 2).map((b, i) =>
                  typeof b === "string" ? (
                    <p key={i} className="mt-2 text-gray-300/90">{b}</p>
                  ) : null
                )}
              </>
            ) : (
              <p className="text-gray-400">Pro insight rotates weekly.</p>
            )}
          </div>
          <Link
            href="/insights"
            className="mt-4 inline-block text-sm font-semibold text-kos-gold hover:underline"
          >
            Browse Insights →
          </Link>
        </div>
      </div>

      {/* Highlighted game articles — 3–5 cards with edge preview + link */}
      <div className="mt-6">
        <h3 className="text-lg font-bebas text-kos-gold tracking-wide mb-4">Highlighted Games</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {HIGHLIGHTED_GAMES.map((g) => (
            <EdgeBoardPreview
              key={g.slug}
              row={g.row}
              articleHref={`/pro/articles/${g.slug}`}
            />
          ))}
        </div>
      </div>

      {/* Cards grid */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {cards.map((c) => {
          const isGold = c.accent === "gold";
          const border = isGold ? "border-kos-gold/25 hover:border-kos-gold/45" : "border-kos-green/20 hover:border-kos-green/40";
          const glow = isGold ? "hover:shadow-kos-gold/20" : "hover:shadow-kos-green/20";
          const title = isGold ? "text-kos-gold" : "text-kos-green";

          return (
            <Link
              key={c.title}
              href={c.href}
              className={[
                "group rounded-3xl border bg-black/30 backdrop-blur-xl p-6 shadow-xl transition",
                border,
                glow,
              ].join(" ")}
            >
              <div className={["text-2xl font-bebas tracking-tight", title].join(" ")}>
                {c.title}
              </div>
              <div className="mt-2 text-sm text-gray-200/80 leading-relaxed">{c.desc}</div>
              <div className="mt-4 text-sm font-semibold text-gray-300 group-hover:text-white transition">
                Open →
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
