import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import { getLineCurve } from "@/lib/line-curve/service";
import { closed } from "@/lib/line-curve/guardrails";
import type {
  LineCurveSport,
  ModelMarginInput,
  OddsAltSnapshot,
} from "@/lib/line-curve/types";
import { pageDataCacheHeaders } from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

function unauthorized() {
  return NextResponse.json(
    { error: "Unauthorized" },
    { status: 401, headers: pageDataCacheHeaders({ cacheable: false }) },
  );
}

function noStore(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: pageDataCacheHeaders({ cacheable: false }),
  });
}

export async function GET(req: Request) {
  const access = await getProAccessState();
  if (access !== "authorized") return unauthorized();

  const url = new URL(req.url);
  if (url.searchParams.get("fixture")) {
    return noStore(
      {
        researchOnly: true,
        curve: closed(
          "unavailable_alt_market",
          "Research fixtures are test-only and are not served on this route.",
        ),
      },
      200,
    );
  }

  // GET cannot carry a model bind. Do not fetch alternate_spreads (Odds API
  // credits) and then fail closed — require POST(snapshot + model).
  return noStore({
    researchOnly: true,
    curve: closed(
      "missing_model_run",
      "No live alternate-spread snapshot bound to a model run. POST an injected snapshot + model to price; do not invent a curve.",
    ),
  });
}

export async function POST(req: Request) {
  const access = await getProAccessState();
  if (access !== "authorized") return unauthorized();

  let body: {
    eventId?: string;
    side?: string;
    book?: string;
    sport?: LineCurveSport;
    snapshot?: OddsAltSnapshot;
    model?: ModelMarginInput;
    fixture?: string;
  } = {};
  try {
    body = (await req.json()) as typeof body;
  } catch {
    body = {};
  }

  if (body.fixture) {
    return noStore({
      researchOnly: true,
      curve: closed(
        "unavailable_alt_market",
        "Research fixtures are test-only and are not served on this route.",
      ),
    });
  }

  if (!body.eventId || !body.side || !body.book || !body.model) {
    return noStore({
      researchOnly: true,
      curve: closed(
        "missing_model_run",
        "eventId, side, book, and a bound model run are required before any live odds fetch.",
      ),
    });
  }

  const curve = await getLineCurve(body.eventId, body.side, body.book, {
    sport: body.sport,
    snapshot: body.snapshot,
    model: body.model,
  });
  return noStore({ researchOnly: true, curve });
}
