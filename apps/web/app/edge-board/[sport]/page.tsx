import Link from "next/link";
import { headers } from "next/headers";
import EdgeBoard, { type EdgeBoardRow } from "@/components/EdgeBoard";
import SportProHeader from "@/components/pro/SportProHeader";
import { NflDataFreshnessBanner } from "@/components/pro/NflDataFreshnessBanner";
import { env } from "@/lib/config/env";
import { assembleEdgeBoardRows } from "@/lib/build-edge-board-rows";
import { getKeiCode, getKeiProductLabel } from "@/lib/kei-brand";
import {
  resolveSportKey,
  sportDisplayLabel,
  SPORTS,
} from "@/lib/sports";
import { getSportOverviewHref } from "@/lib/sport-pro-nav";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

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

async function getRows(
  sport: string,
  slate: "live" | "all",
): Promise<EdgeBoardRow[]> {
  // NFL: assemble directly from fair-lines + Odds (avoids empty Open/Best from stale API cache).
  if (sport.toLowerCase() === "nfl") {
    return assembleEdgeBoardRows("nfl", [], { slate });
  }

  const origin = await getRequestOrigin();
  const headersObj: Record<string, string> = { accept: "application/json" };
  if (env.INTERNAL_API_SECRET)
    headersObj["x-kosedge-secret"] = env.INTERNAL_API_SECRET;

  let res: Response;
  try {
    res = await upstreamFetch(`${origin}/api/edge-board/${sport}/today`, {
      cache: "no-store",
      headers: headersObj,
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
    });
  } catch {
    return [];
  }

  if (!res.ok) return [];

  const json = (await res.json()) as EdgeBoardApiResponse;
  let rows: EdgeBoardRow[] = [];
  if (Array.isArray(json)) rows = json;
  else if (
    json &&
    typeof json === "object" &&
    "rows" in json &&
    Array.isArray((json as { rows?: unknown }).rows)
  ) {
    rows = (json as { rows: EdgeBoardRow[] }).rows;
  }

  return assembleEdgeBoardRows(sport, rows);
}

export default async function EdgeBoardSportPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport?: string }> | { sport?: string };
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const resolved =
    params && typeof (params as Promise<unknown>).then === "function"
      ? await (params as Promise<{ sport?: string }>)
      : ((params as { sport?: string }) ?? {});
  const sportKey = resolveSportKey(resolved?.sport, "ncaam");
  const sportName = sportDisplayLabel(sportKey);
  const keiCode = getKeiCode(sportKey);

  const sp =
    searchParams &&
    typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<
          Record<string, string | string[] | undefined>
        >)
      : ((searchParams as Record<string, string | string[] | undefined>) ?? {});
  const slateRaw = Array.isArray(sp.slate) ? sp.slate[0] : sp.slate;
  const slate: "live" | "all" =
    sportKey === "nfl" && slateRaw === "all" ? "all" : "live";

  const rows = await getRows(sportKey, slate);
  const gameCount = new Set(rows.map((r) => r.game).filter(Boolean)).size;

  const isNfl = sportKey === "nfl";

  const slateLabel =
    sportKey === "nfl" || sportKey === "cfb" ? "Weekly Slate" : "Daily Slate";

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      <SportProHeader activeSport={sportKey} />
      {isNfl ? <NflDataFreshnessBanner /> : null}
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
        <div className="absolute inset-0 bg-linear-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 w-full px-5 sm:px-6 pt-6 pb-16 sm:pt-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div>
            <div className="text-sm text-gray-400">
              {sportName} · Model vs Market · {getKeiProductLabel(sportKey)} ·
              ET
            </div>
            <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight text-kos-gold">
              {sportName} Edge Board
            </h1>
            <p className="mt-2 text-sm sm:text-base text-gray-200/80 max-w-3xl">
              {isNfl
                ? slate === "live"
                  ? `Central research board for the current week. ${keiCode} lines always; Open/Best/separation when books post. You make the picks.`
                  : `All NFL games with sportsbook odds on file. Research board — not a picks feed.`
                : `Model vs market hierarchy. Live Open/Best when books post. ${keiCode} Line and O/U are Kosedge projections — research, not picks.`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={getSportOverviewHref(sportKey)}
              className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
            >
              {sportName} Overview
            </Link>
            <Link
              href={`/pro/${sportKey}/slate/today`}
              className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
            >
              {slateLabel}
            </Link>
            <Link
              href={`/odds/${sportKey}`}
              className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
            >
              Compare Odds
            </Link>
          </div>
        </div>

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

        {sportKey === "nfl" ? (
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/edge-board/nfl"
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                slate === "live"
                  ? "bg-edge-green/20 border border-edge-green/40 text-edge-green"
                  : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
              }`}
            >
              Current week
            </Link>
            <Link
              href="/edge-board/nfl?slate=all"
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                slate === "all"
                  ? "bg-kos-gold/20 border border-kos-gold/50 text-kos-gold"
                  : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
              }`}
            >
              Odds slate
            </Link>
          </div>
        ) : null}

        <EdgeBoard variant="full" rows={rows} sportKey={sportKey} />

        <p className="mt-6 text-xs text-gray-500">
          {rows.length
            ? `${gameCount} games${
                sportKey === "nfl"
                  ? slate === "live"
                    ? " · current week"
                    : " · with sportsbook odds"
                  : ""
              }`
            : "No live data: add ODDS_API_KEY in Vercel → Project Settings → Environment Variables."}
        </p>
      </main>
    </div>
  );
}
