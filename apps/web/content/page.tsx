// app/edge-board/page.tsx
import Link from "next/link";
import Image from "next/image";

type Sport = "NCAAM" | "NFL" | "NBA" | "NHL" | "MLB";

type Row = {
  sport: Sport;
  date: string;
  time: string;
  teamA: string;
  teamB: string;

  openLine: string;
  openOU: string;

  bestLineBook: "DK" | "FD" | "MGM";
  bestLine: string;
  bestOU: string;

  keiLine: string;
  keiOU: string;

  edgeLine: string;
  edgeOU: string;

  tagLine: "PASS" | "LEAN" | "PLAY";
  tagOU: "PASS" | "LEAN" | "PLAY";

  // expandable sections
  overview: string;
  stats: Array<{ k: string; a: string; b: string }>;
};

const rows: Row[] = [
  {
    sport: "NCAAM",
    date: "Feb 8",
    time: "8:30pm",
    teamA: "Team A (KEICMBR)",
    teamB: "Team B (KEICMBR)",

    openLine: "+1.5",
    openOU: "o/u 155",

    bestLineBook: "DK",
    bestLine: "+3.5",
    bestOU: "o156.5",

    keiLine: "+5.5",
    keiOU: "o157",

    edgeLine: "-2.0",
    edgeOU: "+0.5",

    tagLine: "PASS",
    tagOU: "PASS",

    overview:
      "Placeholder overview: injuries, pace, shot profile, rebounding matchup, and one key betting note. No picks—just context.",
    stats: [
      { k: "Tempo Rank", a: "42", b: "118" },
      { k: "AdjOE", a: "114.2", b: "108.8" },
      { k: "AdjDE", a: "101.5", b: "104.9" },
      { k: "Reb%", a: "52.1%", b: "49.3%" },
    ],
  },
];

function TagPill({ tag }: { tag: Row["tagLine"] }) {
  const base =
    "inline-flex items-center justify-center rounded-lg px-2.5 py-1 text-xs font-bebas tracking-wide border";
  if (tag === "PLAY") {
    return (
      <span
        className={`${base} border-kos-green/50 text-kos-green bg-kos-green/10`}
      >
        PLAY
      </span>
    );
  }
  if (tag === "LEAN") {
    return (
      <span
        className={`${base} border-kos-gold/50 text-kos-gold bg-kos-gold/10`}
      >
        LEAN
      </span>
    );
  }
  return (
    <span className={`${base} border-white/15 text-gray-300 bg-white/5`}>
      PASS
    </span>
  );
}

function BookLogo({ book }: { book: Row["bestLineBook"] }) {
  // Put these files in /public/books/ :
  // dk.png, fd.png, mgm.png
  const src =
    book === "DK"
      ? "/books/dk.png"
      : book === "FD"
        ? "/books/fd.png"
        : "/books/mgm.png";

  return (
    <div className="relative h-6 w-6 overflow-hidden rounded-md ring-1 ring-white/10 bg-black/30">
      <Image src={src} alt={book} fill className="object-contain p-0.5" />
    </div>
  );
}

export default function EdgeBoardPage() {
  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      {/* background */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/10 blur-3xl" />
        <div className="absolute top-24 -left-40 h-[520px] w-[520px] rounded-full bg-kos-green/10 blur-3xl" />
        <div className="absolute -bottom-56 -right-56 h-[640px] w-[640px] rounded-full bg-kos-gold/10 blur-3xl" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/55 via-transparent to-black/70" />
      </div>

      {/* header */}
      <header className="relative z-20 border-b border-white/10 bg-black/35 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-5 sm:px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3" aria-label="Home">
            <div className="relative h-10 w-10 rounded-full overflow-hidden ring-1 ring-white/10">
              <Image
                src="/brand/kosedge-logo-v2.png"
                alt="Kos Edge"
                fill
                className="object-cover"
              />
            </div>
            <div className="leading-none">
              <div className="text-xl font-bebas tracking-wider">
                <span className="text-kos-green">KOS</span>{" "}
                <span className="text-kos-gold">EDGE</span>
                <span className="text-gray-400 text-base font-normal">
                  {" "}
                  ANALYTICS
                </span>
              </div>
              <div className="text-xs text-gray-400/80 -mt-0.5">Edge Board</div>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <Link
              href="/methodology"
              className="hidden sm:inline-flex text-sm font-medium text-gray-300 hover:text-kos-gold transition"
            >
              Methodology
            </Link>
            <Link
              href="/pro"
              className="px-4 py-2 rounded-lg font-bold text-sm text-black bg-kos-gold hover:brightness-110 transition shadow-lg shadow-kos-gold/25"
            >
              Become Pro
            </Link>
          </div>
        </div>
      </header>

      {/* body */}
      <main className="relative z-10 max-w-7xl mx-auto px-5 sm:px-6 pt-8 pb-16">
        <div className="flex items-end justify-between gap-6 flex-wrap">
          <div>
            <h1 className="text-4xl sm:text-5xl font-bebas tracking-tight">
              Today&apos;s <span className="text-kos-gold">Edge Board</span>
            </h1>
            <p className="mt-2 text-sm sm:text-base text-gray-300 max-w-2xl">
              Full board view with expandable game notes and key betting stats.
              No picks—just data and context.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Sport:</span>
            <span className="text-xs px-2.5 py-1 rounded bg-white/5 border border-white/10 text-gray-200">
              NCAAM
            </span>
          </div>
        </div>

        {/* Desktop table */}
        <div className="mt-6 hidden lg:block">
          <div className="bg-black/35 border border-white/12 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-[1100px] w-full text-sm">
                <thead className="bg-white/5 text-gray-300">
                  <tr className="text-left">
                    <th className="py-3 px-4">Sport</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Time</th>
                    <th className="py-3 px-4">Team A (KEI)</th>
                    <th className="py-3 px-4">Team B (KEI)</th>

                    <th className="py-3 px-4">Open Line</th>
                    <th className="py-3 px-4">Open O/U</th>

                    <th className="py-3 px-4">Best</th>
                    <th className="py-3 px-4">Best Line</th>
                    <th className="py-3 px-4">Best O/U</th>

                    <th className="py-3 px-4">KEAM Line</th>
                    <th className="py-3 px-4">KEAM O/U</th>

                    <th className="py-3 px-4">Edge Line</th>
                    <th className="py-3 px-4">Edge O/U</th>

                    <th className="py-3 px-4">Tag Line</th>
                    <th className="py-3 px-4">Tag O/U</th>

                    <th className="py-3 px-4">Details</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-white/10 text-gray-100">
                  {rows.map((r, idx) => (
                    <tr key={idx} className="hover:bg-white/5 transition">
                      <td className="py-3 px-4 text-gray-300">{r.sport}</td>
                      <td className="py-3 px-4 text-gray-300">{r.date}</td>
                      <td className="py-3 px-4 text-gray-300">{r.time}</td>

                      <td className="py-3 px-4">{r.teamA}</td>
                      <td className="py-3 px-4">{r.teamB}</td>

                      <td className="py-3 px-4 text-gray-200">{r.openLine}</td>
                      <td className="py-3 px-4 text-gray-200">{r.openOU}</td>

                      <td className="py-3 px-4">
                        <BookLogo book={r.bestLineBook} />
                      </td>
                      <td className="py-3 px-4 font-semibold">{r.bestLine}</td>
                      <td className="py-3 px-4 font-semibold">{r.bestOU}</td>

                      <td className="py-3 px-4 font-semibold text-gray-200">
                        {r.keiLine}
                      </td>
                      <td className="py-3 px-4 font-semibold text-gray-200">
                        {r.keiOU}
                      </td>

                      <td className="py-3 px-4 font-bold text-[#22c55e]">
                        {r.edgeLine}
                      </td>
                      <td className="py-3 px-4 font-bold text-[#22c55e]">
                        {r.edgeOU}
                      </td>

                      <td className="py-3 px-4">
                        <TagPill tag={r.tagLine} />
                      </td>
                      <td className="py-3 px-4">
                        <TagPill tag={r.tagOU} />
                      </td>

                      <td className="py-3 px-4">
                        <details className="group">
                          <summary className="cursor-pointer text-kos-gold hover:brightness-110 select-none">
                            Overview / Stats
                          </summary>
                          <div className="mt-3 text-xs text-gray-300 space-y-3">
                            <p className="leading-relaxed">{r.overview}</p>
                            <div className="rounded-xl border border-white/10 overflow-hidden">
                              <div className="grid grid-cols-3 bg-white/5 text-gray-300">
                                <div className="px-3 py-2">Stat</div>
                                <div className="px-3 py-2">{r.teamA}</div>
                                <div className="px-3 py-2">{r.teamB}</div>
                              </div>
                              {r.stats.map((s, i) => (
                                <div
                                  key={i}
                                  className="grid grid-cols-3 border-t border-white/10"
                                >
                                  <div className="px-3 py-2">{s.k}</div>
                                  <div className="px-3 py-2">{s.a}</div>
                                  <div className="px-3 py-2">{s.b}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="px-4 py-3 text-xs text-gray-400 border-t border-white/10">
              Placeholder data. Links + live odds + rankings will be wired next.
            </div>
          </div>
        </div>

        {/* Mobile condensed cards */}
        <div className="mt-6 lg:hidden space-y-4">
          {rows.map((r, idx) => (
            <div
              key={idx}
              className="bg-black/35 border border-white/12 rounded-2xl p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs text-gray-400">
                    {r.sport} • {r.date} • {r.time}
                  </div>
                  <div className="mt-2 font-semibold">{r.teamA}</div>
                  <div className="text-gray-300">{r.teamB}</div>
                </div>
                <TagPill tag={r.tagLine} />
              </div>

              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <div className="text-xs text-gray-400">Best Line</div>
                  <div className="mt-1 flex items-center gap-2">
                    <BookLogo book={r.bestLineBook} />
                    <div className="font-semibold">{r.bestLine}</div>
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <div className="text-xs text-gray-400">KEAM Line</div>
                  <div className="mt-1 font-semibold">{r.keiLine}</div>
                </div>

                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <div className="text-xs text-gray-400">Edge Line</div>
                  <div className="mt-1 font-bold text-[#22c55e]">
                    {r.edgeLine}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                  <div className="text-xs text-gray-400">Edge O/U</div>
                  <div className="mt-1 font-bold text-[#22c55e]">
                    {r.edgeOU}
                  </div>
                </div>
              </div>

              <details className="mt-3">
                <summary className="cursor-pointer text-kos-gold select-none">
                  Overview / Stats
                </summary>
                <div className="mt-3 text-sm text-gray-300 space-y-3">
                  <p className="text-sm leading-relaxed">{r.overview}</p>
                  <div className="rounded-xl border border-white/10 overflow-hidden">
                    <div className="grid grid-cols-3 bg-white/5 text-gray-300 text-xs">
                      <div className="px-3 py-2">Stat</div>
                      <div className="px-3 py-2">A</div>
                      <div className="px-3 py-2">B</div>
                    </div>
                    {r.stats.map((s, i) => (
                      <div
                        key={i}
                        className="grid grid-cols-3 border-t border-white/10 text-xs"
                      >
                        <div className="px-3 py-2">{s.k}</div>
                        <div className="px-3 py-2">{s.a}</div>
                        <div className="px-3 py-2">{s.b}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </details>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
