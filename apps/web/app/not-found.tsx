// apps/web/app/not-found.tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 font-inter relative overflow-hidden">
      {/* Background FX - matching your exact style */}
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

      <main className="relative z-10 flex min-h-screen items-center justify-center px-5 py-16">
        <div className="w-full max-w-md">
          <div className="bg-black/30 border border-white/12 rounded-2xl p-8 backdrop-blur-xl shadow-xl text-center">
            <h1 className="text-6xl font-bebas tracking-tight text-kos-gold mb-4">
              404
            </h1>
            <h2 className="text-2xl font-bebas tracking-tight text-gray-200 mb-2">
              Page Not Found
            </h2>
            <p className="text-gray-300 mb-6">
              The page you&apos;re looking for doesn&apos;t exist or has been
              moved.
            </p>
            <div className="flex flex-col gap-3">
              <Link
                href="/"
                className="rounded-xl bg-kos-gold px-6 py-3 font-bold text-black hover:brightness-110 transition shadow-lg shadow-kos-gold/25"
              >
                Go Home
              </Link>
              <Link
                href="/edge-board"
                className="rounded-xl bg-white/5 border border-white/12 px-6 py-3 font-semibold hover:border-kos-gold/35 hover:bg-white/10 transition"
              >
                View Edge Board
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
