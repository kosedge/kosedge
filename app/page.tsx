import Link from "next/link";

type Accent = "gold" | "green";

const pillars = [
  {
    title: "Best-Line First",
    desc: "We shop books and price the market. The number is the product, not the pick.",
    accent: "gold" as Accent,
  },
  {
    title: "Edge Discipline",
    desc: 'No "locks". No chasing. Plays only when value clears a real threshold.',
    accent: "green" as Accent,
  },
  {
    title: "Track Everything",
    desc: "CLV-minded workflow with sizing tools and clean tracking for long-term winners.",
    accent: "gold" as Accent,
  },
] as const;

const accentClass = (accent: Accent) => {
  if (accent === "green") {
    return {
      borderHover: "hover:border-kos-green/60",
      title: "text-kos-green",
      glow: "shadow-kos-green/15",
    };
  }

  return {
    borderHover: "hover:border-kos-gold/60",
    title: "text-kos-gold",
    glow: "shadow-kos-gold/15",
  };
};

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-black via-gray-950 to-black text-gray-100 font-inter relative overflow-hidden">
      {/* Subtle bg glows */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="w-full h-full bg-[radial-gradient(circle_at_20%_30%,rgba(34,197,94,0.12)_0%,transparent_60%),radial-gradient(circle_at_80%_70%,rgba(245,185,66,0.12)_0%,transparent_60%)] animate-pulse-slow" />
        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(245,185,66,0.18) 1px, transparent 1px), linear-gradient(to bottom, rgba(245,185,66,0.10) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
      </div>

      {/* Header */}
      <header className="relative z-20 border-b border-gray-800 bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-12">
            <h1 className="text-4xl font-bebas tracking-wider">
              <span className="text-kos-green">KOS</span>{" "}
              <span className="text-kos-gold">EDGE</span>{" "}
              <span className="text-gray-400 text-2xl font-inter font-normal">
                ANALYTICS
              </span>
            </h1>

            <nav className="hidden md:flex items-center gap-10 text-base font-medium text-gray-300">
              <Link href="/methodology" className="hover:text-kos-gold transition">
                Methodology
              </Link>
              <Link href="/insights" className="hover:text-kos-gold transition">
                Insights
              </Link>
              <Link href="/about" className="hover:text-kos-gold transition">
                About
              </Link>
              <Link href="/disclaimer" className="hover:text-kos-gold transition">
                Disclaimer
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-5">
            <Link
              href="/insights"
              className="px-5 py-2.5 text-sm font-medium rounded-lg border border-kos-gold/60 text-kos-gold hover:bg-kos-gold/10 transition"
            >
              Read Insights
            </Link>

            <Link
              href="/pro"
              className="px-6 py-3 bg-gradient-to-r from-kos-green to-kos-dark-green rounded-lg font-bold text-white hover:brightness-110 transition shadow-lg shadow-kos-green/30"
            >
              Get Edge Alerts
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-24">
        <div className="text-center mb-16">
          <h2 className="text-6xl md:text-8xl font-bebas tracking-tight leading-none drop-shadow-lg">
            Beat the number with{" "}
            <span className="text-kos-gold">real edge</span>.
          </h2>

          <p className="mt-8 text-xl md:text-2xl text-gray-300 max-w-4xl mx-auto font-medium">
            Data-driven sports betting built around best-line shopping, strict thresholds,
            bankroll tools, and tracking that respects the long game.
          </p>

          <p className="mt-4 text-xl text-kos-gold font-semibold italic">
            Sharper Data. Smarter Bets.
          </p>
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row justify-center gap-6 mb-20">
          <Link
            href="/pro"
            className="px-10 py-5 bg-kos-gold text-black font-bebas text-2xl rounded-xl shadow-2xl shadow-kos-gold/50 hover:scale-[1.03] transition hover:brightness-110 text-center"
          >
            Today&apos;s Edge Board
          </Link>

          <Link
            href="/methodology"
            className="px-10 py-5 bg-gray-900/70 border border-kos-gold/50 rounded-xl font-semibold text-lg text-kos-gold hover:bg-gray-800 transition text-center"
          >
            How the Model Works
          </Link>
        </div>

        {/* Content grid */}
        <div className="grid md:grid-cols-12 gap-8">
          {/* Left */}
          <div className="md:col-span-7 space-y-8">
            {/* Pillars */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {pillars.map((p) => {
                const a = accentClass(p.accent);
                return (
                  <div
                    key={p.title}
                    className={[
                      "bg-gray-900/70 backdrop-blur-lg border border-gray-800 rounded-2xl p-7 transition",
                      a.borderHover,
                      "shadow-xl",
                      a.glow,
                    ].join(" ")}
                  >
                    <h3 className={["text-2xl font-bebas mb-3", a.title].join(" ")}>
                      {p.title}
                    </h3>
                    <p className="text-gray-400">{p.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Philosophy */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-gradient-to-br from-emerald-950/60 to-gray-900/70 border border-kos-gold/30 rounded-2xl p-8">
                <h3 className="text-3xl font-bebas text-kos-gold mb-4">What you get</h3>
                <p className="text-gray-200 text-lg">
                  Best lines, edge thresholds, disciplined sizing, and clean tracking that
                  fits a serious workflow.
                </p>
              </div>

              <div className="bg-gradient-to-br from-red-950/50 to-gray-900/70 border border-red-800/30 rounded-2xl p-8">
                <h3 className="text-3xl font-bebas text-red-400 mb-4">What we avoid</h3>
                <p className="text-gray-200 text-lg">
                  Hype picks, “lock” talk, chasing, and gimmicks that don’t scale.
                </p>
              </div>
            </div>
          </div>

          {/* Right: Edge Board */}
          <div className="md:col-span-5">
            <div className="bg-gray-900/80 backdrop-blur-xl border border-kos-gold/40 rounded-2xl p-7 shadow-2xl shadow-kos-gold/20">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-3xl font-bebas text-kos-gold">Edge Board</h3>
                <span className="text-sm text-gray-400">
                  Green = value • <span className="text-kos-gold">Gold = premium</span>
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-base">
                  <thead>
                    <tr className="border-b border-gray-700 text-left text-gray-400 font-medium">
                      <th className="pb-4 pr-6">Game</th>
                      <th className="pb-4 pr-6">Best</th>
                      <th className="pb-4 pr-6">Model</th>
                      <th className="pb-4 pr-6">Edge</th>
                      <th className="pb-4">Tag</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-800">
                    <tr>
                      <td className="py-4 pr-6">Duke vs UNC</td>
                      <td className="py-4 pr-6">-2.5</td>
                      <td className="py-4 pr-6">-4.0</td>
                      <td className="py-4 pr-6 text-emerald-400 font-bold">+1.5</td>
                      <td className="py-4 text-kos-gold font-bebas font-bold">LEAN</td>
                    </tr>

                    <tr>
                      <td className="py-4 pr-6">LAL vs BOS</td>
                      <td className="py-4 pr-6">o216.5</td>
                      <td className="py-4 pr-6">223.0</td>
                      <td className="py-4 pr-6 text-emerald-400 font-bold">+4.5</td>
                      <td className="py-4 text-emerald-400 font-bold font-bebas">PLAY</td>
                    </tr>

                    <tr>
                      <td className="py-4 pr-6">PHI vs NYM</td>
                      <td className="py-4 pr-6">+105</td>
                      <td className="py-4 pr-6">+120</td>
                      <td className="py-4 pr-6 text-emerald-400 font-bold">+7.1%</td>
                      <td className="py-4 text-emerald-400 font-bold font-bebas">PLAY</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="mt-6 text-sm text-gray-500">
                Sample board for now. Next step is wiring this to live data + tracking.
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-gray-800 bg-black/60 backdrop-blur py-10">
        <div className="max-w-7xl mx-auto px-6 text-center text-gray-500">
          <p className="text-lg font-medium text-kos-gold">Sharper Data. Smarter Bets.</p>
          <p className="mt-2">© {new Date().getFullYear()} KOS Edge Analytics</p>
        </div>
      </footer>
    </div>
  );
}