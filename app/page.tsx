import Link from "next/link";

type Accent = "gold" | "green";

const pillars = [
  {
    title: "Best Lines First",
    desc: "We shop books and price the market. The Number is the product.",
    accent: "gold" as Accent,
  },
  {
    title: "Edge Discipline",
    desc: "No locks. No chasing. Plays only when Edge clears real thresholds.",
    accent: "green" as Accent,
  },
  {
    title: "Models vs Vegas",
    desc: "Independent models across sports, measured against market prices.",
    accent: "gold" as Accent,
  },
] as const;

function accentClass(accent: Accent) {
  if (accent === "green") {
    return {
      borderHover: "hover:border-kos-green/60",
      title: "text-kos-green",
    };
  }
  return {
    borderHover: "hover:border-kos-gold/60",
    title: "text-kos-gold",
  };
}

export default function Home() {
  return (
    <div className="min-h-screen bg-linear-to-b from-black via-gray-950 to-black text-gray-100 font-inter relative overflow-hidden">
      {/* Background FX */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="w-full h-full opacity-70 sm:opacity-100 bg-[radial-gradient(circle_at_20%_30%,rgba(245,185,66,0.08)_0%,transparent_60%),radial-gradient(circle_at_80%_70%,rgba(34,197,94,0.06)_0%,transparent_60%)]" />
      </div>

      {/* Header */}
      <header className="relative z-20 border-b border-gray-800 bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-8 sm:gap-10">
            {/* Logo + Wordmark */}
            <Link href="/" className="flex items-center gap-4">
              <img
                src="/brand/kosedge-logo.png"
                alt="KosEdge"
                className="h-9 w-9"
              />
              <h1 className="text-3xl font-bebas tracking-wider leading-none">
                <span className="text-kos-green">KOS</span>{" "}
                <span className="text-kos-gold">EDGE</span>{" "}
                <span className="text-gray-400 text-xl font-inter font-normal">
                  ANALYTICS
                </span>
              </h1>
            </Link>

            <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-300">
              <Link href="/edge-board" className="hover:text-kos-gold transition">
                Edge Board
              </Link>
              <Link
                href="/methodology"
                className="hover:text-kos-gold transition"
              >
                Methodology
              </Link>
              <Link href="/about" className="hover:text-kos-gold transition">
                About
              </Link>
              <Link href="/disclaimer" className="hover:text-kos-gold transition">
                Disclaimer
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            <Link
              href="/edge-board"
              className="px-4 sm:px-5 py-2 text-sm font-medium rounded-lg border border-gray-700 text-gray-300 hover:border-kos-gold hover:text-kos-gold transition"
            >
              View Edge Board
            </Link>
            <Link
              href="/pro"
              className="px-5 sm:px-6 py-2.5 bg-kos-gold text-black rounded-lg font-bold hover:brightness-110 transition"
            >
              Go Pro
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 pt-12 sm:pt-20 pb-16 sm:pb-24">
        <div className="text-center mb-10 sm:mb-14">
          <h2 className="text-5xl sm:text-6xl md:text-8xl font-bebas tracking-tight leading-tight md:leading-none">
            Beat the <span className="text-kos-gold">Number</span> with real{" "}
            <span className="text-kos-gold">Edge</span>.
          </h2>

          <p className="mt-6 sm:mt-7 text-lg sm:text-xl md:text-2xl text-gray-300 max-w-4xl mx-auto font-medium">
            Data-driven sports betting built around best-line shopping,
            threshold-based models, and a unified Edge Board designed for
            long-term bettors.
          </p>

          <p className="mt-4 text-lg text-gray-400 italic">
            Sharper Data. Smarter Bets.
          </p>
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row justify-center gap-4 sm:gap-6 mb-12 sm:mb-16">
          <Link
            href="/edge-board"
            className="px-8 sm:px-10 py-4 sm:py-5 bg-kos-gold text-black font-bebas text-xl sm:text-2xl rounded-xl shadow-xl hover:scale-[1.03] transition text-center"
          >
            Today&apos;s Edge Board
          </Link>
          <Link
            href="/methodology"
            className="px-8 sm:px-10 py-4 sm:py-5 bg-gray-900 border border-gray-700 rounded-xl font-semibold text-base sm:text-lg text-gray-300 hover:border-kos-gold hover:text-kos-gold transition text-center"
          >
            How the Models Work
          </Link>
        </div>

        {/* Pillars */}
        <div className="grid sm:grid-cols-3 gap-4 sm:gap-6 mb-12 sm:mb-16">
          {pillars.map((p) => {
            const a = accentClass(p.accent);
            return (
              <div
                key={p.title}
                className={`bg-gray-900/70 border border-gray-800 rounded-2xl p-6 sm:p-7 transition ${a.borderHover}`}
              >
                <h3 className={`text-2xl font-bebas mb-3 ${a.title}`}>
                  {p.title}
                </h3>
                <p className="text-gray-400">{p.desc}</p>
              </div>
            );
          })}
        </div>

        {/* Edge Board Preview */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-5 sm:p-7 shadow-xl">
          <h3 className="text-2xl sm:text-3xl font-bebas text-kos-gold mb-3 sm:mb-4">
            Edge Board (Sample)
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-sm sm:text-base">
              <thead>
                <tr className="border-b border-gray-700 text-left text-gray-400">
                  <th className="pb-3 pr-4 sm:pr-6">Game</th>
                  <th className="pb-3 pr-4 sm:pr-6">Best</th>
                  <th className="pb-3 pr-4 sm:pr-6">Model</th>
                  <th className="pb-3 pr-4 sm:pr-6">Edge</th>
                  <th className="pb-3">Tag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                <tr>
                  <td className="py-4 pr-4 sm:pr-6">Duke vs UNC</td>
                  <td className="py-4 pr-4 sm:pr-6">-2.5</td>
                  <td className="py-4 pr-4 sm:pr-6">-4.0</td>
                  <td className="py-4 pr-4 sm:pr-6 text-kos-green font-bold">
                    +1.5
                  </td>
                  <td className="py-4 font-bebas text-kos-gold">LEAN</td>
                </tr>
                <tr>
                  <td className="py-4 pr-4 sm:pr-6">LAL vs BOS</td>
                  <td className="py-4 pr-4 sm:pr-6">o216.5</td>
                  <td className="py-4 pr-4 sm:pr-6">223.0</td>
                  <td className="py-4 pr-4 sm:pr-6 text-kos-green font-bold">
                    +4.5
                  </td>
                  <td className="py-4 font-bebas text-kos-green">PLAY</td>
                </tr>
                <tr>
                  <td className="py-4 pr-4 sm:pr-6">PHI vs NYM</td>
                  <td className="py-4 pr-4 sm:pr-6">+105</td>
                  <td className="py-4 pr-4 sm:pr-6">+120</td>
                  <td className="py-4 pr-4 sm:pr-6 text-kos-green font-bold">
                    +7.1%
                  </td>
                  <td className="py-4 font-bebas text-kos-green">PLAY</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="mt-4 text-sm text-gray-500">
            Sample board for now. Next step is wiring this to live data + tracking.
          </p>
        </div>
      </main>
    </div>
  );
}