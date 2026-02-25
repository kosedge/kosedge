#!/usr/bin/env bash
set -euo pipefail

echo "==> Restoring canonical components under apps/web/components"

mkdir -p apps/web/components

# Remove broken barrels (they referenced deleted folders)
rm -f apps/web/components/index.ts
rm -f apps/web/components/edge-board/index.ts
rm -f apps/web/components/pro/index.ts

# ----------------------------
# EdgeBoard.tsx
# ----------------------------
cat > apps/web/components/EdgeBoard.tsx <<'TS'
import * as React from "react";

export type EdgeBoardRow = {
  id?: string;
  game?: string;      // "Duke @ UNC"
  time?: string;      // "7:00 PM"
  market?: string;    // "Spread" / "Total" / "ML"
  open?: string;      // "-3.5" / "145.5"
  best?: string;      // "-4" / "146"
  book?: string;      // "DK" / "FD"
  note?: string;      // optional tag / status
};

export type EdgeBoardVariant = "home" | "full";

export type EdgeBoardProps = {
  variant?: EdgeBoardVariant;
  rows?: EdgeBoardRow[];
};

/**
 * EdgeBoard
 * - Server Component friendly (no client hooks needed)
 * - Renders a "home" compact preview OR a "full" board table
 * - Safe defaults and stable props for future scalability
 */
export default function EdgeBoard({ variant = "full", rows = [] }: EdgeBoardProps) {
  const isHome = variant === "home";

  const header = (
    <div className="flex items-start justify-between gap-3">
      <div>
        <div className="text-sm text-gray-400">
          {isHome ? "Sample Edge Board" : "Live Edge Board"}
        </div>
        <h2 className="text-3xl sm:text-4xl font-bebas tracking-tight text-kos-gold">
          {isHome ? "Today’s Slate Preview" : "Today’s Edge Board"}
        </h2>
        <p className="mt-1 text-xs sm:text-sm text-gray-200/70">
          {isHome
            ? "A visual preview of the Pro experience."
            : "No picks. Just market numbers: Open vs Best."}
        </p>
      </div>

      <div className="hidden sm:block text-xs text-gray-500">
        {rows.length ? `${rows.length} games` : "Awaiting feed"}
      </div>
    </div>
  );

  const EmptyState = (
    <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 backdrop-blur-xl p-5">
      <div className="text-sm text-gray-300/90 font-semibold">No rows yet</div>
      <div className="mt-1 text-xs text-gray-400">
        If the API is offline or returning empty, you’ll see this placeholder.
      </div>

      {/* Nice looking placeholder rows for the homepage */}
      {isHome && (
        <div className="mt-4 grid gap-3">
          {[
            { game: "Team A @ Team B", time: "7:00 PM", market: "Spread", open: "-2.5", best: "-3" },
            { game: "Team C @ Team D", time: "8:30 PM", market: "Total", open: "145.5", best: "146" },
            { game: "Team E @ Team F", time: "9:00 PM", market: "ML", open: "+120", best: "+130" },
          ].map((r, i) => (
            <div
              key={i}
              className="rounded-xl border border-white/10 bg-black/25 px-4 py-3 flex items-center justify-between"
            >
              <div>
                <div className="text-sm text-gray-100 font-semibold">{r.game}</div>
                <div className="text-xs text-gray-400">{r.time} • {r.market}</div>
              </div>
              <div className="text-xs text-gray-300">
                <span className="text-gray-500">Open</span> {r.open}{" "}
                <span className="mx-2 opacity-40">→</span>{" "}
                <span className="text-gray-500">Best</span> {r.best}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const Table = (
    <div className="mt-5 overflow-hidden rounded-2xl border border-white/10 bg-black/30 backdrop-blur-xl shadow-xl">
      <div className="grid grid-cols-12 gap-2 px-4 py-3 border-b border-white/10 text-[11px] text-gray-400 uppercase tracking-wider">
        <div className="col-span-5">Game</div>
        <div className="col-span-2">Time</div>
        <div className="col-span-2">Market</div>
        <div className="col-span-1 text-right">Open</div>
        <div className="col-span-1 text-right">Best</div>
        <div className="col-span-1 text-right">Book</div>
      </div>

      <div className="divide-y divide-white/10">
        {rows.slice(0, isHome ? 6 : rows.length).map((r, idx) => (
          <div
            key={r.id ?? `${r.game ?? "row"}-${idx}`}
            className="grid grid-cols-12 gap-2 px-4 py-3 text-sm"
          >
            <div className="col-span-5">
              <div className="text-gray-100 font-semibold">{r.game ?? "—"}</div>
              {r.note ? <div className="text-xs text-gray-400 mt-0.5">{r.note}</div> : null}
            </div>
            <div className="col-span-2 text-gray-300/90">{r.time ?? "—"}</div>
            <div className="col-span-2 text-gray-300/90">{r.market ?? "—"}</div>
            <div className="col-span-1 text-right text-gray-200">{r.open ?? "—"}</div>
            <div className="col-span-1 text-right text-kos-gold font-semibold">{r.best ?? "—"}</div>
            <div className="col-span-1 text-right text-gray-400">{r.book ?? "—"}</div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <section
      className={[
        "bg-black/25 border border-white/10 rounded-3xl p-5 sm:p-6 backdrop-blur-xl shadow-2xl",
        isHome ? "lg:col-span-5" : "",
      ].join(" ")}
    >
      {header}
      {rows.length ? Table : EmptyState}
    </section>
  );
}
TS

# ----------------------------
# ProPricing.tsx (client component because it sets cookies)
# ----------------------------
cat > apps/web/components/ProPricing.tsx <<'TS'
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

function enableProAndGo() {
  document.cookie = "kosedge_pro=1; path=/; max-age=31536000; samesite=lax";
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
          <span className="text-gray-100"> Edge Boards for all sports</span>,{" "}
          <span className="text-gray-100">game breakdowns</span>,{" "}
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

            {p.sub && <div className="mt-2 text-sm text-gray-300/80">{p.sub}</div>}

            <button
              type="button"
              className={[
                "mt-6 w-full px-4 py-3 rounded-2xl font-semibold transition",
                p.highlight
                  ? "bg-kos-gold text-black hover:brightness-110 shadow-lg shadow-kos-gold/25"
                  : "bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10",
              ].join(" ")}
              onClick={enableProAndGo}
            >
              {p.cta}
            </button>

            <div className="mt-3 text-xs text-gray-500">Cancel anytime • Instant access</div>
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
                <div className="pb-2 text-sm text-gray-400">{yearly.cadence}</div>
              </div>

              <div className="mt-2 text-sm text-gray-200/80">{yearly.sub}</div>
            </div>

            <div className="w-full md:w-[320px]">
              <button
                type="button"
                className="w-full px-4 py-3 rounded-2xl font-semibold bg-kos-gold text-black hover:brightness-110 transition shadow-lg shadow-kos-gold/30"
                onClick={enableProAndGo}
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
TS

# ----------------------------
# ProWelcomeHub.tsx (server-friendly component)
# ----------------------------
cat > apps/web/components/ProWelcomeHub.tsx <<'TS'
import Link from "next/link";
import Image from "next/image";

type HubCard = {
  title: string;
  desc: string;
  href: string;
  accent?: "gold" | "green";
};

const sports = [
  { label: "CBB", href: "/edge-board?league=ncaam" },
  { label: "NBA", href: "/edge-board?league=nba" },
  { label: "NFL", href: "/edge-board?league=nfl" },
  { label: "MLB", href: "/edge-board?league=mlb" },
  { label: "CFB", href: "/edge-board?league=cfb" },
  { label: "WNBA", href: "/edge-board?league=wnba" },
];

const cards: HubCard[] = [
  { title: "Edge Board", desc: "Best lines, open vs best, tags and filters (expanding).", href: "/edge-board", accent: "gold" },
  { title: "Market Dashboard", desc: "Totals, spreads, steam, key numbers, movement snapshots.", href: "/pro/market", accent: "green" },
  { title: "Workflow", desc: "Build a card. Save leans. Track CLV. One-click book links (V1).", href: "/pro/workflow", accent: "gold" },
  { title: "Power Ratings", desc: "Team strength, updates, and historical context.", href: "/pro/power-ratings", accent: "green" },
  { title: "Props", desc: "Prop analyzer and edge screens (V1+).", href: "/pro/props", accent: "gold" },
  { title: "Guides", desc: "Discipline + bankroll + model methodology docs.", href: "/methodology", accent: "green" },
];

export default function ProWelcomeHub() {
  return (
    <section className="w-full">
      {/* Banner */}
      <div className="rounded-3xl border border-white/10 bg-black/30 backdrop-blur-xl p-6 sm:p-7 shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="relative h-16 w-16 sm:h-20 sm:w-20 rounded-full overflow-hidden ring-1 ring-white/10">
              <Image
                src="/brand/kosedge-logo-v2.png"
                alt="Kos Edge Analytics"
                fill
                className="object-cover"
                priority
              />
            </div>

            <div className="leading-none">
              <div className="text-3xl sm:text-4xl font-bebas tracking-wider">
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

          {/* Sport tabs */}
          <div className="flex flex-wrap gap-2 justify-start lg:justify-end">
            {sports.map((s) => (
              <Link
                key={s.label}
                href={s.href}
                className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 hover:border-kos-gold/35 hover:bg-white/10 transition text-sm font-semibold"
              >
                {s.label}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Grid */}
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

      {/* “Top Edge” / article area placeholder */}
      <div className="mt-6 rounded-3xl border border-white/10 bg-black/25 backdrop-blur-xl p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm text-gray-400">Top Edge Article</div>
            <div className="mt-1 text-2xl font-bebas text-kos-gold">Insight of the Week</div>
            <div className="mt-2 text-sm text-gray-200/80 max-w-3xl">
              This is where your featured weekly write-up lives: market angle, matchup breakdown, key numbers,
              and workflow steps.
            </div>
          </div>

          <Link
            href="/insights"
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
          >
            Browse Insights
          </Link>
        </div>
      </div>
    </section>
  );
}
TS

echo "==> 5) Fix imports in pages to use direct file imports (no barrels)"

# Home page: EdgeBoard
perl -0777 -i -pe 's@import\s+EdgeBoard\s+from\s+"@/components";@import EdgeBoard from "@/components/EdgeBoard";@g' apps/web/app/page.tsx || true

# Edge-board page: EdgeBoard + type
perl -0777 -i -pe 's@import\s+EdgeBoard,\s*\{\s*type\s+EdgeBoardRow\s*\}\s+from\s+"@/components";@import EdgeBoard from "@/components/EdgeBoard";\nimport type { EdgeBoardRow } from "@/components/EdgeBoard";@g' apps/web/app/edge-board/page.tsx || true

# Pro pages: ProPricing / ProWelcomeHub
perl -0777 -i -pe 's@from\s+"@/components/ProPricing";@from "@/components/ProPricing";@g' apps/web/app/**/pro/page.tsx 2>/dev/null || true
perl -0777 -i -pe 's@from\s+"@/components/ProWelcomeHub";@from "@/components/ProWelcomeHub";@g' apps/web/app/**/pro/**/page.tsx 2>/dev/null || true

echo "==> 6) Show remaining barrel imports (should be empty or harmless)"
rg 'from "@/components"' apps/web/app -n || true

echo "==> 7) Clean Next caches"
rm -rf apps/web/.next apps/web/.turbo

echo "==> Done. Start the web app with: pnpm dev:web"
