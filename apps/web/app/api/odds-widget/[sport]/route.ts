import { NextResponse } from "next/server";
import { env } from "@/lib/config/env";
import { logError } from "@/lib/logger";
import { getSport } from "@/lib/sports";
import { SPORT_KEY_MAP } from "@/lib/odds-api";

const WIDGET_BASE = "https://widget.the-odds-api.com/v1/sports";
const BOOKMAKERS = "draftkings,fanduel,circa,betmgm,bet365,fanatics,betrivers,betr";
const MARKETS = "h2h,spreads,totals";
const MARKET_NAMES = "h2h:Moneyline,spreads:Spread,totals:Over/Under";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sport: string }> }
) {
  const { sport } = await params;
  const valid = getSport(sport);
  const widgetSportKey = SPORT_KEY_MAP[sport];
  const key = env.ODDS_WIDGET_ACCESS_KEY?.trim();

  if (!valid || !widgetSportKey || !key) {
    return new NextResponse("Widget not configured", { status: 404 });
  }

  const url = `${WIDGET_BASE}/${widgetSportKey}/events/?accessKey=${encodeURIComponent(key)}&bookmakerKeys=${BOOKMAKERS}&oddsFormat=american&markets=${MARKETS}&marketNames=${encodeURIComponent(MARKET_NAMES)}`;

  try {
    const res = await fetch(url, {
      cache: "no-store",
      headers: { accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" },
    });
    if (!res.ok) {
      return new NextResponse(`Widget upstream error: ${res.status}`, { status: 502 });
    }
    const html = await res.text();
    return new NextResponse(html, {
      headers: {
        "content-type": res.headers.get("content-type") ?? "text/html; charset=utf-8",
        "cache-control": "public, s-maxage=3600, stale-while-revalidate=600",
      },
    });
  } catch (e) {
    logError(e instanceof Error ? e : new Error(String(e)), { sport, route: "odds-widget" });
    return new NextResponse("Widget unavailable", { status: 502 });
  }
}
