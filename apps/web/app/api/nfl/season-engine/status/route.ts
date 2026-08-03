import { NextResponse } from "next/server";
import { fetchSeasonEngineStatus } from "@/lib/nfl-season-engine";

export const dynamic = "force-dynamic";

export async function GET() {
  const status = await fetchSeasonEngineStatus();
  if (status.error) {
    return NextResponse.json(status, { status: 502 });
  }
  return NextResponse.json(status);
}
