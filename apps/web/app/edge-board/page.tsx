// apps/web/app/edge-board/page.tsx
import Link from "next/link";
import { headers } from "next/headers";
import EdgeBoard, { type EdgeBoardRow } from "@/components/EdgeBoard";
import { env } from "@/lib/config/env";

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

async function getTonightRows(): Promise<EdgeBoardRow[]> {
  try {
    const origin = await getRequestOrigin();

    const headersObj: Record<string, string> = { accept: "application/json" };
    // If your API route is protected, server components CAN safely attach the secret.
    if (env.INTERNAL_API_SECRET) {
      headersObj["x-kosedge-secret"] = env.INTERNAL_API_SECRET;
    }

    const res = await fetch(`${origin}/api/edge-board/ncaam/today`, {
      cache: "no-store",
      headers: headersObj,
    });

    if (!res.ok) return [];

    const json = (await res.json()) as EdgeBoardApiResponse;

    // ✅ Support both shapes: array OR { rows: [...] }
    if (Array.isArray(json)) return json;
    if (json && typeof json === "object" && "rows" in json && Array.isArray((json as any).rows)) {
      return (json as any).rows as EdgeBoardRow[];
    }

    return [];
  } catch {
    return [];
  }
}

export default async function EdgeBoardPage() {
  const rows = await getTonightRows();

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

      <main className="relative z-10 w-full px-5 sm:px-6 pt-10 pb-16">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="text-sm text-gray-400">NCAAM • Live odds (Open + Best)</div>
            <h1 className="text-5xl font-bebas tracking-tight text-kos-gold">
              Today&apos;s Edge Board
            </h1>
            <p className="mt-2 text-sm sm:text-base text-gray-200/80 max-w-3xl">
              Live: Game/Time/Open/Best. KEICMB + Edge + Tags are coming soon. No picks. Just information.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              ← Home
            </Link>
            <Link
              href="/insights"
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold"
            >
              Insights
            </Link>
            <Link
              href="/pro"
              className="px-4 py-2 rounded-xl bg-kos-gold text-black hover:brightness-110 transition text-center font-semibold shadow-lg shadow-kos-gold/25"
            >
              Become Pro
            </Link>
          </div>
        </div>

        {/* Filters placeholder */}
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

        {/* Board */}
        <EdgeBoard variant="full" rows={rows} />

        <div className="mt-6 text-xs text-gray-500">
          {rows.length ? `Live odds loaded (${rows.length} games).` : "No games returned yet (or API offline)."}
        </div>
      </main>
    </div>
  );
}