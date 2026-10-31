import { NextResponse } from "next/server";
import { env } from "@/lib/config/env";
import { logError } from "@/lib/logger";
import { getSport } from "@/lib/sports";
import { SPORT_KEY_MAP } from "@/lib/odds-api";
import { oddsAcquire } from "@/lib/odds-acquire/acquire";
import { ODDS_WIDGET_HOST } from "@/lib/odds-acquire/hosts";
import { isPaidFetchDenied } from "@/lib/odds-acquire/errors";

const BOOKMAKERS =
  "draftkings,fanduel,betmgm,betrivers,hardrockbet,fanatics,bet365,circa,betr";
const MARKETS = "h2h,spreads,totals";
const MARKET_NAMES = "h2h:Moneyline,spreads:Spread,totals:Over/Under";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sport: string }> },
) {
  const { sport } = await params;
  const valid = getSport(sport);
  const widgetSportKey = SPORT_KEY_MAP[sport];
  const key = env.ODDS_WIDGET_ACCESS_KEY?.trim();

  if (!valid || !widgetSportKey || !key) {
    return new NextResponse("Widget not configured", { status: 404 });
  }

  const qs = new URLSearchParams({
    accessKey: key,
    bookmakerKeys: BOOKMAKERS,
    oddsFormat: "american",
    markets: MARKETS,
    marketNames: MARKET_NAMES,
  });

  try {
    const res = await oddsAcquire({
      host: ODDS_WIDGET_HOST,
      path: `/v1/sports/${widgetSportKey}/events/?${qs.toString()}`,
      caller: `odds-widget:${sport}`,
    });
    if (!res.ok) {
      return new NextResponse(`Widget upstream error: ${res.status}`, {
        status: 502,
      });
    }
    const html = await res.text();
    return new NextResponse(html, {
      headers: {
        "content-type":
          res.headers.get("content-type") ?? "text/html; charset=utf-8",
        "cache-control": "public, s-maxage=3600, stale-while-revalidate=600",
      },
    });
  } catch (e) {
    if (isPaidFetchDenied(e)) {
      return new NextResponse("Widget not configured", { status: 404 });
    }
    logError(e instanceof Error ? e : new Error(String(e)), {
      sport,
      route: "odds-widget",
    });
    return new NextResponse("Widget unavailable", { status: 502 });
  }
}
