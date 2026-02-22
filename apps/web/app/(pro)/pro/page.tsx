// apps/web/app/(pro)/pro/page.tsx
import Link from "next/link";
import { redirect } from "next/navigation";
import ProPricing from "@/components/ProPricing";
import { isProUser } from "@/lib/auth/pro";

export const dynamic = "force-dynamic";

export default async function ProPage() {
  const isPro = await isProUser();
  if (isPro) redirect("/pro/welcome");

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 font-inter relative overflow-hidden">
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

      <main className="relative z-10 w-full px-5 sm:px-6 pt-10 pb-16">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <Link
            href="/"
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
          >
            ← Home
          </Link>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/edge-board"
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              Edge Board
            </Link>
            <Link
              href="/insights"
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              Insights
            </Link>
          </div>
        </div>

        <div className="mt-10">
          <ProPricing />
        </div>

        <div className="mt-8 text-center text-xs text-gray-500">
          Taxes may apply. Cancel anytime. Upgrade/downgrade anytime.
        </div>
      </main>
    </div>
  );
}
