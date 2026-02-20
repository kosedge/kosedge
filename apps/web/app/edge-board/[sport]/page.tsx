import Link from "next/link";
import { headers } from "next/headers";
import EdgeBoard, { type EdgeBoardRow } from "@/components/EdgeBoard";
import { env } from "@/lib/config/env";
import { getSport, SPORTS } from "@/lib/sports";

export const dynamic = "force-dynamic";

async function getRequestOrigin(): Promise<string> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}`;
}

type EdgeBoardApiResponse =
  | EdgeBoardRow[]
  | { rows: EdgeBoardRow[]; cached?: boolean; ttl?: number }
  | { error: string; [k: string]: unknown };

async function getRows(sport: string): Promise<EdgeBoardRow[]> {
  const origin = await getRequestOrigin();
  const headersObj: Record<string, string> = { accept: "application/json" };
  if (env.INTERNAL_API_SECRET) headersObj["x-kosedge-secret"] = env.INTERNAL_API_SECRET;

  const res = await fetch(`${origin}/api/edge-board/${sport}/today`, {
    cache: "no-store",
    headers: headersObj,
  });

  if (!res.ok) return [];

  const json = (await res.json()) as EdgeBoardApiResponse;
  if (Array.isArray(json)) return json;
  if (json && typeof json === "object" && "rows" in json && Array.isArray((json as { rows?: unknown }).rows)) {
    return (json as { rows: EdgeBoardRow[] }).rows;
  }
  return [];
}

export default async function EdgeBoardSportPage({
  params,
}: { params: Promise<{ sport?: string }> | { sport?: string } }) {
  const resolved = params && typeof (params as Promise<unknown>).then === "function"
    ? await (params as Promise<{ sport?: string }>)
    : (params as { sport?: string }) ?? {};
  const sportKey = String(resolved?.sport ?? "ncaam");
  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const rows = await getRows(sportKey);

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
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div>
            <div className="text-sm text-gray-400">{sportName} • Live odds (Open + Best)</div>
            <h1 className="text-5xl font-bebas tracking-tight text-kos-gold">
              Today&apos;s Edge Board
            </h1>
            <p className="mt-2 text-sm sm:text-base text-gray-200/80 max-w-3xl">
              Live: Game/Time/Open/Best. KEICMB + Edge + Tags coming with model.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              ← Home
            </Link>
            <Link
              href={`/pro/${sportKey}`}
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              {sportName} Hub
            </Link>
            <Link
              href={`/odds/${sportKey}`}
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              Compare Odds
            </Link>
            <Link
              href="/pro/welcome"
              className="px-4 py-2 rounded-xl bg-kos-gold text-black hover:brightness-110 transition text-center font-semibold shadow-lg shadow-kos-gold/25"
            >
              Pro
            </Link>
          </div>
        </div>

        {/* Sport switcher */}
        <div className="mt-6 flex flex-wrap gap-2">
          {SPORTS.map((s) => (
            <Link
              key={s.key}
              href={`/edge-board/${s.key}`}
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                s.key === sportKey
                  ? "bg-kos-gold/20 border border-kos-gold/50 text-kos-gold"
                  : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
              }`}
            >
              {s.label}
            </Link>
          ))}
        </div>

        <EdgeBoard variant="full" rows={rows} />

        <p className="mt-6 text-xs text-gray-500">
          {rows.length ? `${rows.length} games` : "Placeholder. Wire model for live data."}
        </p>
      </main>
    </div>
  );
}
