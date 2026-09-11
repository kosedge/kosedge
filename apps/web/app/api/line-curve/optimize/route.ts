import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import {
  optimizeMissouriOklahomaLineCurve,
  optimizeTwoLegLineCurve,
} from "@/lib/line-curve/service";
import type { QuotedParlayPrice, TwoLegInput } from "@/lib/line-curve/types";
import { pageDataCacheHeaders } from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

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

  if (body.fixture === "missouri-oklahoma") {
    return NextResponse.json(
      {
        researchOnly: true,
        fixture: "missouri-oklahoma",
        result: optimizeMissouriOklahomaLineCurve(),
      },
      { headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  if (!body.legA || !body.legB || !body.book) {
    return NextResponse.json(
      { error: "legA, legB, and book are required" },
      { status: 400, headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  const result = optimizeTwoLegLineCurve(body.legA, body.legB, body.book, {
    quotedParlays: body.quotedParlays,
  });
  return NextResponse.json(
    { researchOnly: true, result },
    { headers: pageDataCacheHeaders({ cacheable: false }) },
  );
}
