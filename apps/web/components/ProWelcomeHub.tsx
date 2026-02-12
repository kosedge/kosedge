// apps/web/components/ProWelcomeHub.tsx

"use client";

import Link from "next/link";

type BookLine = {
  book: string;
  line: string;
  juice: string;
  url: string;
};

type EdgeItem = {
  game: string;
  modelLine: string;
  bestMarketLine: string;
  edge: string;
  books: BookLine[];
};

const sampleEdge: EdgeItem = {
  game: "Duke @ UNC",
  modelLine: "-4.5",
  bestMarketLine: "-2.5",
  edge: "+2.0",
  books: [
    { book: "DraftKings", line: "-2.5", juice: "-110", url: "#" },
    { book: "FanDuel", line: "-2.5", juice: "-108", url: "#" },
    { book: "BetMGM", line: "-3.0", juice: "-110", url: "#" },
  ],
};

export default function ProWelcomeHub() {
  return (
    <div className="space-y-10">

      {/* ================= MARKET DASHBOARD ================= */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <div className="bg-black/40 border border-white/10 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-xs text-gray-400">Active Edges Today</div>
          <div className="text-4xl font-bebas text-kos-gold mt-2">42</div>
          <div className="text-xs text-gray-500 mt-1">
            Spread 18 • Total 9 • Props 15
          </div>
        </div>

        <div className="bg-black/40 border border-white/10 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-xs text-gray-400">Largest Edge</div>
          <div className="text-4xl font-bebas text-kos-green mt-2">+3.4%</div>
          <div className="text-xs text-gray-500 mt-1">
            CBB • Spread
          </div>
        </div>

        <div className="bg-black/40 border border-white/10 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-xs text-gray-400">Most Active Sport</div>
          <div className="text-4xl font-bebas text-gray-100 mt-2">NCAAM</div>
          <div className="text-xs text-gray-500 mt-1">
            22 edges detected
          </div>
        </div>

      </section>

      {/* ================= BEST LINE PANEL ================= */}
      <section className="bg-black/50 border border-kos-gold/30 rounded-3xl p-8 backdrop-blur-xl shadow-xl shadow-kos-gold/20">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">

          <div>
            <div className="text-sm text-gray-400">Top Edge Right Now</div>
            <div className="text-3xl font-bebas text-kos-gold mt-1">
              {sampleEdge.game}
            </div>

            <div className="mt-4 space-y-1 text-sm">
              <div>Model Line: <span className="text-gray-100">{sampleEdge.modelLine}</span></div>
              <div>Best Market Line: <span className="text-gray-100">{sampleEdge.bestMarketLine}</span></div>
              <div>Edge: <span className="text-kos-green font-bold">{sampleEdge.edge}</span></div>
            </div>
          </div>

          <div className="w-full lg:w-[380px] space-y-3">
            {sampleEdge.books.map((b) => (
              <a
                key={b.book}
                href={b.url}
                className="flex items-center justify-between px-4 py-3 rounded-2xl bg-white/5 border border-white/10 hover:border-kos-gold/40 transition"
              >
                <div>
                  <div className="font-semibold text-gray-100">{b.book}</div>
                  <div className="text-xs text-gray-400">
                    {b.line} ({b.juice})
                  </div>
                </div>
                <div className="text-kos-gold font-semibold">
                  Bet →
                </div>
              </a>
            ))}
          </div>

        </div>
      </section>

      {/* ================= WORKFLOW ================= */}
      <section className="bg-black/30 border border-white/10 rounded-3xl p-8 backdrop-blur-xl">
        <div className="text-2xl font-bebas text-kos-gold">
          Pro Workflow
        </div>

        <div className="mt-6 grid grid-cols-1 md:grid-cols-5 gap-4 text-sm text-gray-300">
          <div>1. Scan Edge Board</div>
          <div>2. Filter by Edge %</div>
          <div>3. Confirm Line Movement</div>
          <div>4. Review Breakdown</div>
          <div>5. Bet Best Number</div>
        </div>
      </section>

      {/* ================= TOOL GRID ================= */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-5">

        {[
          "Edge Board",
          "Power Ratings",
          "Odds Screen",
          "Props Analyzer",
          "DFS Model",
          "Futures Dashboard",
          "Betting Guide",
          "Historical Performance"
        ].map((tool) => (
          <Link
            key={tool}
            href="/edge-board"
            className="bg-black/40 border border-white/10 rounded-2xl p-6 hover:border-kos-gold/40 transition backdrop-blur-xl"
          >
            <div className="text-lg font-semibold text-gray-100">
              {tool}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              Open →
            </div>
          </Link>
        ))}

      </section>

      {/* ================= CONTENT GRID ================= */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <div className="lg:col-span-2 bg-black/40 border border-white/10 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-xl font-bebas text-kos-gold">
            Featured Article
          </div>
          <div className="mt-4 text-gray-300">
            Why Duke vs UNC is mispriced by 2 points tonight.
          </div>
          <Link href="/insights" className="text-kos-gold text-sm mt-4 inline-block">
            Read →
          </Link>
        </div>

        <div className="bg-black/40 border border-white/10 rounded-3xl p-6 backdrop-blur-xl">
          <div className="text-xl font-bebas text-kos-gold">
            Insight of the Week
          </div>
          <div className="mt-4 text-gray-300">
            Power rating shifts after conference play.
          </div>
          <Link href="/insights" className="text-kos-gold text-sm mt-4 inline-block">
            View →
          </Link>
        </div>

      </section>

    </div>
  );
}