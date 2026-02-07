// app/page.tsx
import Link from "next/link";
import Image from "next/image";
import EdgeBoard from "@/components/EdgeBoard";

type Accent = "gold" | "green";

const pillars: Array<{ title: string; desc: string; accent: Accent }> = [
  {
    title: "Best-Line First",
    desc: "We shop books and price the market. The number is the product, not the pick.",
    accent: "gold",
  },
  {
    title: "Edge Discipline",
    desc: 'No "locks." No chasing. Plays only when value clears a real threshold.',
    accent: "green",
  },
  {
    title: "Models vs Vegas",
    desc: "We measure our projections against market lines to find mispriced numbers—then act.",
    accent: "gold",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 font-inter relative overflow-hidden">
      {/* Background FX */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/12 blur-3xl animate-pulse-slow" />
        <div className="absolute top-24 -left-40 h-[520px] w-[520px] rounded-full bg-kos-green/10 blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-56 -right-56 h-[640px] w-[640px] rounded-full bg-kos-gold/10 blur-3xl animate-pulse-slow" />

        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(245,185,66,0.18) 1px, transparent 1px), linear-gradient(to bottom, rgba(245,185,66,0.10) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70" />
      </div>

      {/* Header */}
      <header className="relative z-20 border-b border-white/10 bg-black/35 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-5 sm:px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-3 sm:gap-4"
            aria-label="Kos Edge Analytics Home"
          >
            <div className="relative h-14 w-14 sm:h-16 sm:w-16 rounded-full overflow-hidden ring-1 ring-white/10">
              <Image
                src="/brand/kosedge-logo-v2.png"
                alt="Kos Edge Analytics"
                fill
                className="object-cover"
                priority
              />
            </div>

            <div className="leading-none">
              <div className="text-2xl sm:text-3xl font-bebas tracking-wider">
                <span className="text-kos-green">KOS</span>{" "}
                <span className="text-kos-gold">EDGE</span>{" "}
                <span className="text-gray-400 text-xl sm:text-2xl font-inter font-normal">
                  ANALYTICS
                </span>
              </div>
              <div className="text-xs sm:text-sm text-gray-400/80 -mt-0.5">
                Beat the <span className="text-white">Number</span> with real{" "}
                <span className="text-kos-gold">Edge</span>
              </div>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-300">
            <Link href="/insights" className="hover:text-kos-gold transition">
              Insights
            </Link>
            <Link href="/about" className="hover:text-kos-gold transition">
              About
            </Link>
            <Link href="/methodology" className="hover:text-kos-gold transition">
              Methodology
            </Link>
            <Link href="/disclaimer" className="hover:text-kos-gold transition">
              Disclaimer
            </Link>
          </nav>

          <div className="flex items-center gap-3 sm:gap-4">
            {/* TOP LINK #1: Edge Board (next to Become Pro) */}
            <Link
              href="/edge-board"
              className="hidden sm:inline-flex px-4 py-2 text-sm font-semibold rounded-lg border border-kos-gold/45 text-kos-gold hover:bg-kos-gold/10 transition"
            >
              Edge Board
            </Link>

            <Link
              href="/pro"
              className="px-4 sm:px-5 py-2.5 rounded-lg font-bold text-sm text-black bg-kos-gold hover:brightness-110 transition shadow-lg shadow-kos-gold/25"
            >
              Become Pro
            </Link>
          </div>
        </div>

        <div className="md:hidden border-t border-white/10">
          <div className="max-w-7xl mx-auto px-5 py-3 flex items-center justify-between text-sm text-gray-300">
            <Link href="/insights" className="hover:text-kos-gold transition">
              Insights
            </Link>
            <Link href="/about" className="hover:text-kos-gold transition">
              About
            </Link>
            <Link href="/methodology" className="hover:text-kos-gold transition">
              Methodology
            </Link>
            <Link href="/disclaimer" className="hover:text-kos-gold transition">
              Disclaimer
            </Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <main className="relative z-10 max-w-7xl mx-auto px-5 sm:px-6 pt-10 sm:pt-14 pb-16 sm:pb-20">
        <div className="grid lg:grid-cols-12 gap-8 lg:gap-10 items-start">
          <div className="lg:col-span-7">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bebas tracking-tight leading-[0.95]">
              Beat the <span className="text-white">Number</span> with real{" "}
              <span className="text-kos-gold">Edge</span>.
            </h1>

            <p className="mt-5 sm:mt-6 text-lg sm:text-xl text-gray-200/90 max-w-2xl">
              Data-driven sports betting built around best-line shopping, strict thresholds,
              bankroll tools, and tracking that respects the long game.
            </p>

            <p className="mt-3 text-base sm:text-lg text-kos-gold font-semibold italic">
              Sharper Data. Smarter Bets.
            </p>

            <div className="mt-6 sm:mt-8 flex flex-col sm:flex-row gap-3 sm:gap-4">
              {/* LINK #2: Today’s Edge Board */}
              <Link
                href="/edge-board"
                className="px-7 py-4 rounded-xl bg-kos-gold text-black font-bebas text-2xl text-center shadow-2xl shadow-kos-gold/35 hover:brightness-110 hover:scale-[1.02] transition"
              >
                Today&apos;s Edge Board
              </Link>

              <Link
                href="/methodology"
                className="px-7 py-4 rounded-xl bg-black/30 border border-white/15 text-white font-semibold text-center hover:border-kos-gold/35 hover:bg-black/40 transition"
              >
                How the Model Works
              </Link>
            </div>

            <div className="mt-5 text-sm text-gray-400">
              Threshold-based. Long-term focused. Built for disciplined bettors.
            </div>
          </div>

          {/* Homepage visual: sample Edge Board card */}
          <EdgeBoard variant="home" />
        </div>

        <div className="mt-10 sm:mt-12 grid lg:grid-cols-12 gap-6 lg:gap-8">
          <div className="lg:col-span-7 space-y-6">
            <div className="grid sm:grid-cols-3 gap-4 sm:gap-5">
              {pillars.map((p) => {
                const isGold = p.accent === "gold";
                const ringGlow = isGold
                  ? "hover:border-kos-gold/60 hover:shadow-kos-gold/25 shadow-kos-gold/20"
                  : "hover:border-kos-green/60 hover:shadow-kos-green/25 shadow-kos-green/20";
                const title = isGold ? "text-kos-gold" : "text-kos-green";
                const icon = isGold ? "text-kos-gold" : "text-kos-green";

                return (
                  <div
                    key={p.title}
                    className={[
                      "bg-black/30 border border-white/12 rounded-2xl p-5 backdrop-blur-xl shadow-xl transition",
                      ringGlow,
                    ].join(" ")}
                  >
                    <div className={["text-sm font-semibold", icon].join(" ")}>●</div>
                    <h3 className={["mt-2 text-2xl font-bebas", title].join(" ")}>
                      {p.title}
                    </h3>
                    <p className="mt-2 text-sm text-gray-200/80 leading-relaxed">{p.desc}</p>
                  </div>
                );
              })}
            </div>

            <div className="grid sm:grid-cols-2 gap-4 sm:gap-5">
              <div className="bg-black/30 border border-white/12 rounded-2xl p-6 backdrop-blur-xl shadow-xl">
                <h3 className="text-2xl font-bebas text-kos-gold">What you get</h3>
                <p className="mt-2 text-sm text-gray-200/85 leading-relaxed">
                  Best lines, edge thresholds, disciplined sizing, and clean tracking that fits a
                  serious workflow.
                </p>
              </div>

              <div className="bg-black/30 border border-white/12 rounded-2xl p-6 backdrop-blur-xl shadow-xl">
                <h3 className="text-2xl font-bebas text-red-400">What we avoid</h3>
                <p className="mt-2 text-sm text-gray-200/85 leading-relaxed">
                  Hype picks, “lock” talk, chasing, and gimmicks that don’t scale.
                </p>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5">
            <div className="bg-black/30 border border-white/12 rounded-2xl p-6 backdrop-blur-xl shadow-xl">
              <h3 className="text-2xl font-bebas text-kos-gold">One board. Every sport.</h3>
              <p className="mt-2 text-sm text-gray-200/85 leading-relaxed">
                Behind the scenes, each sport has its own model. Up front, everything flows into the
                same Edge Board so your workflow stays consistent.
              </p>

              <div className="mt-4 flex flex-col sm:flex-row gap-3">
                <Link
                  href="/edge-board"
                  className="px-4 py-3 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
                >
                  View the Edge Board
                </Link>
                <Link
                  href="/pro"
                  className="px-4 py-3 rounded-xl bg-kos-gold text-black hover:brightness-110 transition text-center font-semibold shadow-lg shadow-kos-gold/20"
                >
                  Become Pro
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="relative z-10 border-t border-white/10 bg-black/35 backdrop-blur py-10">
        <div className="max-w-7xl mx-auto px-6 text-center text-gray-400">
          <p className="text-lg font-medium text-kos-gold">Sharper Data. Smarter Bets.</p>
          <p className="mt-2 text-sm">© {new Date().getFullYear()} KOS Edge Analytics</p>
        </div>
      </footer>
    </div>
  );
}