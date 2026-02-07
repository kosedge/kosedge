// components/EdgeBoard.tsx
import Link from "next/link";
import Image from "next/image";

type Variant = "home" | "full";

type EdgeBoardRow = {
  id: string;
  game: string;
  time?: string;
  bestSpread?: string;      // e.g. +3.5 (DK)
  bestTotal?: string;       // e.g. o156.5 (DK)
  keiRankA?: string;        // KEICMBR
  keiRankB?: string;        // KEICMBR
  keiLine?: string;         // KEAMB Line
  keiTotal?: string;        // KEAMB O/U
  edgeLine?: string;        // Edge Line
  edgeOU?: string;          // Edge O/U
  tagLine?: "PLAY" | "LEAN" | "PASS";
  tagOU?: "PLAY" | "LEAN" | "PASS";
};

const sampleRows: EdgeBoardRow[] = [
  {
    id: "1",
    game: "Duke vs UNC",
    time: "8:30pm",
    bestSpread: "-2.5",
    bestTotal: "o156.5",
    keiRankA: "12",
    keiRankB: "18",
    keiLine: "-4.0",
    keiTotal: "157",
    edgeLine: "+1.5",
    edgeOU: "+0.5",
    tagLine: "LEAN",
    tagOU: "PASS",
  },
  {
    id: "2",
    game: "LAL vs BOS",
    time: "7:00pm",
    bestSpread: "+1.0",
    bestTotal: "o216.5",
    keiRankA: "—",
    keiRankB: "—",
    keiLine: "-3.5",
    keiTotal: "223",
    edgeLine: "+4.5",
    edgeOU: "+6.5",
    tagLine: "PLAY",
    tagOU: "PLAY",
  },
  {
    id: "3",
    game: "PHI vs NYM",
    time: "1:10pm",
    bestSpread: "+105",
    bestTotal: "o7.5",
    keiRankA: "—",
    keiRankB: "—",
    keiLine: "+120",
    keiTotal: "8.1",
    edgeLine: "+7.1%",
    edgeOU: "+0.6",
    tagLine: "PLAY",
    tagOU: "LEAN",
  },
];

function tagPill(tag?: string) {
  if (!tag) return "bg-white/5 text-gray-300 border-white/10";
  if (tag === "PLAY") return "bg-[#15803d]/20 text-[#22c55e] border-[#22c55e]/25";
  if (tag === "LEAN") return "bg-kos-gold/15 text-kos-gold border-kos-gold/25";
  return "bg-white/5 text-gray-300 border-white/10";
}

export default function EdgeBoard({ variant = "full" }: { variant?: Variant }) {
  // green styling (hex, so it always shows)
  const edgeGreen =
    "font-bold text-[#22c55e] drop-shadow-[0_0_10px_rgba(34,197,94,0.55)]";
  const playGreen =
    "text-[#22c55e] drop-shadow-[0_0_12px_rgba(34,197,94,0.65)]";

  if (variant === "home") {
    // HOME: keep the “pretty” sample card (what you already had)
    return (
      <div className="lg:col-span-5">
        <div className="relative">
          <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-kos-gold/25 via-kos-green/15 to-kos-gold/25 blur-2xl opacity-80" />

          <div className="relative bg-black/40 border border-white/12 rounded-3xl p-5 sm:p-6 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-3xl font-bebas text-kos-gold">Edge Board</h2>
              <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-gray-400">
                Sample
              </span>
            </div>

            <div className="overflow-hidden rounded-2xl border border-white/10">
              <table className="w-full text-sm sm:text-base">
                <thead className="bg-white/5">
                  <tr className="text-left text-gray-300">
                    <th className="py-3 px-4">Game</th>
                    <th className="py-3 px-4">Best</th>
                    <th className="py-3 px-4">Model</th>
                    <th className="py-3 px-4">Edge</th>
                    <th className="py-3 px-4">Tag</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-white/10 text-gray-200">
                  <tr className="hover:bg-white/5 transition">
                    <td className="py-3 px-4">Duke vs UNC</td>
                    <td className="py-3 px-4">-2.5</td>
                    <td className="py-3 px-4">-4.0</td>
                    <td className={`py-3 px-4 ${edgeGreen}`}>+1.5</td>
                    <td className="py-3 px-4 font-bebas text-kos-gold tracking-wide">
                      LEAN
                    </td>
                  </tr>

                  <tr className="hover:bg-white/5 transition">
                    <td className="py-3 px-4">LAL vs BOS</td>
                    <td className="py-3 px-4">o216.5</td>
                    <td className="py-3 px-4">223.0</td>
                    <td className={`py-3 px-4 ${edgeGreen}`}>+4.5</td>
                    <td className={`py-3 px-4 font-bebas tracking-wide ${playGreen}`}>
                      PLAY
                    </td>
                  </tr>

                  <tr className="hover:bg-white/5 transition">
                    <td className="py-3 px-4">PHI vs NYM</td>
                    <td className="py-3 px-4">+105</td>
                    <td className="py-3 px-4">+120</td>
                    <td className={`py-3 px-4 ${edgeGreen}`}>+7.1%</td>
                    <td className={`py-3 px-4 font-bebas tracking-wide ${playGreen}`}>
                      PLAY
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="mt-4 text-xs text-gray-400">
              Sample data for illustrative purposes only. The real Edge Board is updated daily with
              new games, numbers, and insights across multiple sports.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // FULL: dedicated Edge Board page (big table + mobile condensed)
  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-6 py-10">
      {/* Top bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm text-gray-400">NCAAM • Placeholder</div>
          <h1 className="text-5xl font-bebas tracking-tight text-kos-gold">
            Today&apos;s Edge Board
          </h1>
          <p className="mt-2 text-sm sm:text-base text-gray-200/80 max-w-3xl">
            Best lines + model lines + edge tags. Overview/Stats expanders will live here next.
            No picks. Just information.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href="/"
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
          >
            Back Home
          </Link>
          <Link
            href="/pro"
            className="px-4 py-2 rounded-xl bg-kos-gold text-black hover:brightness-110 transition text-center font-semibold shadow-lg shadow-kos-gold/20"
          >
            Become Pro
          </Link>
        </div>
      </div>

      {/* Filters / placeholders row */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-black/30 border border-white/12 rounded-2xl p-4 backdrop-blur-xl">
          <div className="text-xs text-gray-400">Sport</div>
          <div className="mt-1 font-semibold text-gray-200">NCAAM</div>
        </div>
        <div className="bg-black/30 border border-white/12 rounded-2xl p-4 backdrop-blur-xl">
          <div className="text-xs text-gray-400">Date</div>
          <div className="mt-1 font-semibold text-gray-200">Today</div>
        </div>
        <div className="bg-black/30 border border-white/12 rounded-2xl p-4 backdrop-blur-xl">
          <div className="text-xs text-gray-400">Search</div>
          <div className="mt-1 text-gray-400">Coming soon (team, conference, market)</div>
        </div>
      </div>

      {/* Desktop “full” table */}
      <div className="mt-6 hidden lg:block">
        <div className="bg-black/30 border border-white/12 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl">
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
            <div className="text-sm text-gray-300">
              Full Board • KEI placeholders (KEICMB / KEICMBR)
            </div>
            <div className="text-xs text-gray-500">Logos + links next</div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-[1100px] w-full text-sm">
              <thead className="bg-white/5 text-gray-300">
                <tr className="text-left">
                  <th className="py-3 px-4">Game</th>
                  <th className="py-3 px-4">Time</th>
                  <th className="py-3 px-4">Best Line</th>
                  <th className="py-3 px-4">Best O/U</th>
                  <th className="py-3 px-4">KEICMBR A</th>
                  <th className="py-3 px-4">KEICMBR B</th>
                  <th className="py-3 px-4">KEAMB Line</th>
                  <th className="py-3 px-4">KEAMB O/U</th>
                  <th className="py-3 px-4">Edge Line</th>
                  <th className="py-3 px-4">Edge O/U</th>
                  <th className="py-3 px-4">Tag Line</th>
                  <th className="py-3 px-4">Tag O/U</th>
                  <th className="py-3 px-4">Overview</th>
                  <th className="py-3 px-4">Stats</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-white/10 text-gray-200">
                {sampleRows.map((r) => (
                  <tr key={r.id} className="hover:bg-white/5 transition">
                    <td className="py-3 px-4 font-semibold">{r.game}</td>
                    <td className="py-3 px-4 text-gray-300">{r.time ?? "—"}</td>

                    {/* Best lines: placeholders for book logos + deep links */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="h-5 w-5 rounded bg-white/10 border border-white/10 grid place-items-center text-[10px] text-gray-300">
                          DK
                        </div>
                        <a
                          href="#"
                          className="underline decoration-white/20 hover:decoration-kos-gold/60"
                          title="Will link to sportsbook line page"
                        >
                          {r.bestSpread ?? "—"}
                        </a>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="h-5 w-5 rounded bg-white/10 border border-white/10 grid place-items-center text-[10px] text-gray-300">
                          DK
                        </div>
                        <a
                          href="#"
                          className="underline decoration-white/20 hover:decoration-kos-gold/60"
                          title="Will link to sportsbook total page"
                        >
                          {r.bestTotal ?? "—"}
                        </a>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-gray-300">{r.keiRankA ?? "—"}</td>
                    <td className="py-3 px-4 text-gray-300">{r.keiRankB ?? "—"}</td>

                    <td className="py-3 px-4">{r.keiLine ?? "—"}</td>
                    <td className="py-3 px-4">{r.keiTotal ?? "—"}</td>

                    <td className={`py-3 px-4 ${edgeGreen}`}>{r.edgeLine ?? "—"}</td>
                    <td className={`py-3 px-4 ${edgeGreen}`}>{r.edgeOU ?? "—"}</td>

                    <td className="py-3 px-4">
                      <span
                        className={[
                          "inline-flex items-center justify-center px-2 py-1 rounded-lg border text-xs font-semibold",
                          tagPill(r.tagLine),
                        ].join(" ")}
                      >
                        {r.tagLine ?? "—"}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={[
                          "inline-flex items-center justify-center px-2 py-1 rounded-lg border text-xs font-semibold",
                          tagPill(r.tagOU),
                        ].join(" ")}
                      >
                        {r.tagOU ?? "—"}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <button
                        className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-xs font-semibold"
                        type="button"
                        title="Dropdown coming soon"
                      >
                        Overview ▾
                      </button>
                    </td>
                    <td className="py-3 px-4">
                      <button
                        className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-xs font-semibold"
                        type="button"
                        title="Dropdown coming soon"
                      >
                        Stats ▾
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="px-5 py-4 text-xs text-gray-400 border-t border-white/10">
            Placeholder layout. Next: sportsbook logos + deep links, then real data wiring, then
            Overview/Stats expanders (no picks).
          </div>
        </div>
      </div>

      {/* Mobile condensed board */}
      <div className="mt-6 lg:hidden">
        <div className="bg-black/30 border border-white/12 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl">
          <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
            <div className="text-sm text-gray-300">Mobile Board (Condensed)</div>
            <div className="text-xs text-gray-500">Placeholder</div>
          </div>

          <div className="divide-y divide-white/10">
            {sampleRows.map((r) => (
              <div key={r.id} className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-gray-200">{r.game}</div>
                    <div className="text-xs text-gray-400 mt-1">{r.time ?? "—"}</div>
                  </div>

                  <div className="flex gap-2">
                    <span
                      className={[
                        "inline-flex items-center justify-center px-2 py-1 rounded-lg border text-xs font-semibold",
                        tagPill(r.tagLine),
                      ].join(" ")}
                    >
                      {r.tagLine ?? "—"}
                    </span>
                    <span
                      className={[
                        "inline-flex items-center justify-center px-2 py-1 rounded-lg border text-xs font-semibold",
                        tagPill(r.tagOU),
                      ].join(" ")}
                    >
                      {r.tagOU ?? "—"}
                    </span>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-gray-400">Best Line (DK)</div>
                    <div className="mt-1 font-semibold text-gray-200">{r.bestSpread ?? "—"}</div>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-gray-400">Best O/U (DK)</div>
                    <div className="mt-1 font-semibold text-gray-200">{r.bestTotal ?? "—"}</div>
                  </div>

                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-gray-400">KEAMB Line</div>
                    <div className="mt-1 font-semibold text-gray-200">{r.keiLine ?? "—"}</div>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-gray-400">KEAMB O/U</div>
                    <div className="mt-1 font-semibold text-gray-200">{r.keiTotal ?? "—"}</div>
                  </div>

                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-gray-400">Edge Line</div>
                    <div className={`mt-1 ${edgeGreen}`}>{r.edgeLine ?? "—"}</div>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-gray-400">Edge O/U</div>
                    <div className={`mt-1 ${edgeGreen}`}>{r.edgeOU ?? "—"}</div>
                  </div>
                </div>

                <div className="mt-4 flex gap-2">
                  <button
                    className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-xs font-semibold"
                    type="button"
                  >
                    Overview ▾
                  </button>
                  <button
                    className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-xs font-semibold"
                    type="button"
                  >
                    Stats ▾
                  </button>
                </div>

                <div className="mt-4 text-[11px] text-gray-400">
                  Links/logos + expandable content coming next.
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 text-xs text-gray-500">
        Note: This page is a UI mock with placeholder values to lock layout before live data.
      </div>
    </div>
  );
}