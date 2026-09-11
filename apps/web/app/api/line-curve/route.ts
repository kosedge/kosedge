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

  const eventId = url.searchParams.get("eventId");
  const side = url.searchParams.get("side");
  const book = url.searchParams.get("book");
  if (!eventId || !side || !book) {
    return noStore({
      researchOnly: true,
      curve: closed(
        "missing_odds",
        "No live alternate-spread snapshot bound to a model run. POST an injected snapshot + model to price; do not invent a curve.",
      ),
    });
  }

  const curve = await getLineCurve(eventId, side, book, {
    sport: (url.searchParams.get("sport") as LineCurveSport) || undefined,
  });
  return noStore({ researchOnly: true, curve });
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

  if (!body.eventId || !body.side || !body.book) {
    return noStore(
      { error: "eventId, side, and book are required" },
      400,
    );
  }

  const curve = await getLineCurve(body.eventId, body.side, body.book, {
    sport: body.sport,
    snapshot: body.snapshot,
    model: body.model,
  });
  return noStore({ researchOnly: true, curve });
}
