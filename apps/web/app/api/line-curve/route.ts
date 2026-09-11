import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import {
  getLineCurve,
  getMissouriOklahomaLineCurve,
} from "@/lib/line-curve/service";
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

export async function GET(req: Request) {
  const access = await getProAccessState();
  if (access !== "authorized") return unauthorized();

  const url = new URL(req.url);
  const fixture = url.searchParams.get("fixture");
  const side = url.searchParams.get("side") ?? "Missouri";

  if (fixture === "missouri-oklahoma") {
    const curve = getMissouriOklahomaLineCurve(
      side === "Oklahoma" ? "Oklahoma" : "Missouri",
    );
    return NextResponse.json(
      {
        researchOnly: true,
        fixture: "missouri-oklahoma",
        curve,
      },
      { headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  return NextResponse.json(
    {
      error:
        "Phase 1 Line Curve GET requires fixture=missouri-oklahoma. POST an injected snapshot + model run to price a live event.",
    },
    { status: 400, headers: pageDataCacheHeaders({ cacheable: false }) },
  );
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

  if (body.fixture === "missouri-oklahoma") {
    const curve = getMissouriOklahomaLineCurve(
      body.side === "Oklahoma" ? "Oklahoma" : "Missouri",
    );
    return NextResponse.json(
      {
        researchOnly: true,
        fixture: "missouri-oklahoma",
        curve,
      },
      { headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  if (!body.eventId || !body.side || !body.book) {
    return NextResponse.json(
      { error: "eventId, side, and book are required" },
      { status: 400, headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  const curve = await getLineCurve(body.eventId, body.side, body.book, {
    sport: body.sport,
    snapshot: body.snapshot,
    model: body.model,
  });
  return NextResponse.json(
    { researchOnly: true, curve },
    { headers: pageDataCacheHeaders({ cacheable: false }) },
  );
}
