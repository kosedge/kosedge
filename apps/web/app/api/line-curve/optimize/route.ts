import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import { optimizeTwoLegLineCurve } from "@/lib/line-curve/service";
import { closed } from "@/lib/line-curve/guardrails";
import { lineCurveUnavailablePayload } from "@/lib/line-curve/degrade";
import { jointProbabilityCaption } from "@/lib/line-curve/joint-presentation";
import {
  correlationMeta,
  independentJointModel,
} from "@/lib/line-curve/joint-optimizer";
import type { QuotedParlayPrice, TwoLegInput } from "@/lib/line-curve/types";
import { pageDataCacheHeaders } from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

function noStore(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: pageDataCacheHeaders({ cacheable: false }),
  });
}

export async function POST(req: Request) {
  const access = await getProAccessState();
  if (access !== "authorized") {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401, headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  let body: {
    fixture?: string;
    book?: string;
    legA?: TwoLegInput;
    legB?: TwoLegInput;
    quotedParlays?: QuotedParlayPrice[];
  } = {};
  try {
    body = (await req.json()) as typeof body;
  } catch {
    body = {};
  }

  const independence = correlationMeta(independentJointModel());

  if (body.fixture) {
    return noStore({
      researchOnly: true,
      independenceCaption: jointProbabilityCaption(independence),
      result: closed(
        "unavailable_alt_market",
        "Research fixtures are test-only and are not served on this route.",
      ),
    });
  }

  if (!body.legA || !body.legB || !body.book) {
    // No fixture, no interpolation, no live Odds API fetch.
    return noStore({
      ...lineCurveUnavailablePayload(),
      independenceCaption: jointProbabilityCaption(independence),
      result: closed("unavailable_alt_market", "Market alt prices unavailable"),
    });
  }

  const result = optimizeTwoLegLineCurve(body.legA, body.legB, body.book, {
    quotedParlays: body.quotedParlays,
  });
  return noStore({
    researchOnly: true,
    independenceCaption: result.ok
      ? jointProbabilityCaption(result.correlation)
      : jointProbabilityCaption(independence),
    result,
  });
}
