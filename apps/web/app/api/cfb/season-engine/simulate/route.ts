import { NextResponse } from "next/server";
import { fetchCfbSimulate } from "@/lib/cfb-season-engine";

export const dynamic = "force-dynamic";

function parseBody(raw: unknown): {
  season?: number;
  nSims?: number;
  seed?: number;
  demo?: boolean;
  asOfWeek?: number;
} {
  if (!raw || typeof raw !== "object") return {};
  const body = raw as Record<string, unknown>;
  return {
    season:
      typeof body.season === "number"
        ? body.season
        : typeof body.season === "string"
          ? Number(body.season)
          : undefined,
    nSims:
      typeof body.nSims === "number"
        ? body.nSims
        : typeof body.n_sims === "number"
          ? body.n_sims
          : undefined,
    seed: typeof body.seed === "number" ? body.seed : undefined,
    demo: typeof body.demo === "boolean" ? body.demo : undefined,
    asOfWeek:
      typeof body.asOfWeek === "number"
        ? body.asOfWeek
        : typeof body.as_of_week === "number"
          ? body.as_of_week
          : undefined,
  };
}

export async function POST(req: Request) {
  let raw: unknown = {};
  try {
    raw = await req.json();
  } catch {
    raw = {};
  }
  const body = parseBody(raw);
  const result = await fetchCfbSimulate({
    season: body.season,
    nSims: body.nSims ?? 10,
    seed: body.seed,
    demo: body.demo,
    asOfWeek: body.asOfWeek,
  });
  if (result.error) {
    const status = result.error.includes("must") ? 400 : 502;
    return NextResponse.json(result, { status });
  }
  return NextResponse.json(result);
}
