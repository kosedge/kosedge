import SiteHeader from "@/components/layout/SiteHeader";

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-[#070A0F] text-[#E9EEF5]">
      <SiteHeader />
      <section className="mx-auto max-w-4xl px-6 pt-10 pb-20">
        <h1 className="text-4xl font-extrabold">
          About <span className="text-[#F5B942]">Kos Edge</span>
        </h1>
        <p className="mt-4 text-white/70">
          Kos Edge Analytics was built on a simple belief: Sports betting should
          be intelligent. Not emotional. Not gimmicky. Not based on
          &quot;locks.&quot; Just data, probability, and discipline.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">
          Why This Exists
        </h2>
        <p className="mt-3 text-white/70">
          The betting market is one of the most competitive markets in the
          world. Sportsbooks use models. Sharp bettors use models. Most casual
          bettors don&apos;t. That&apos;s the gap.
        </p>
        <p className="mt-2 text-white/70">
          Kos Edge exists to close it. We build professional-grade projection
          systems and make them usable — not intimidating.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">What We Are</h2>
        <p className="mt-3 text-white/70">We are:</p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>A modeling company</li>
          <li>A simulation engine</li>
          <li>A structured betting framework</li>
          <li>A profitable system</li>
        </ul>
        <p className="mt-3 text-white/70">The model powers everything:</p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Props</li>
          <li>Totals</li>
          <li>Run lines</li>
          <li>Moneylines</li>
          <li>Power ratings</li>
        </ul>
        <p className="mt-3 text-white/70">
          The Edge Board is the interface. The engine is the product.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">
          Who It&apos;s For
        </h2>
        <p className="mt-3 text-white/70">
          This platform is built for two types of bettors:
        </p>
        <p className="mt-3 text-white/70 font-semibold">1. Sharps</p>
        <p className="mt-1 text-white/70">
          If you already understand EV, CLV, and line shopping — this gives you
          structure, scale, and efficiency.
        </p>
        <p className="mt-3 text-white/70 font-semibold">
          2. The Serious Casual
        </p>
        <p className="mt-1 text-white/70">
          If you&apos;re tired of guessing… If you want to understand why
          something is a bet… If you want to graduate from parlays and hype…
          This is your bridge.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">Philosophy</h2>
        <p className="mt-3 text-white/70">
          We don&apos;t promise magic. We promise process.
        </p>
        <p className="mt-2 text-white/70">
          We don&apos;t promise you&apos;ll win every night. We promise that
          betting with edge beats betting without one.
        </p>
        <p className="mt-2 text-white/70">
          We don&apos;t sell emotion. We build models. And the model is
          profitable.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">The Vision</h2>
        <p className="mt-3 text-white/70">
          This isn&apos;t a hobby project. It&apos;s a long-term system.
        </p>
        <p className="mt-2 text-white/70">The goal is to build:</p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Multi-sport projection engines</li>
          <li>Deep simulation models</li>
          <li>Transparent performance tracking</li>
          <li>A platform bettors can trust</li>
        </ul>
        <p className="mt-3 text-white/70">
          Built to scale. Built to last. Built to pass down.
        </p>

        <hr className="my-8 border-white/20" />

        <p className="mt-8 text-white/90 text-lg">
          Built on Data. Driven by Edge.
        </p>
        <p className="mt-2 text-white/90 text-lg">Welcome to Kos Edge.</p>
      </section>
    </main>
  );
}
