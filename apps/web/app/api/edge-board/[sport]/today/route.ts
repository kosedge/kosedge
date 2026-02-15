import { NextResponse } from "next/server";
import { getSport } from "@/lib/sports";

export const dynamic = "force-dynamic";

// Shell: returns empty rows for sports without model. NCAAM hits static api/edge-board/ncaam/today.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sport: string }> }
) {
  const { sport } = await params;
  const valid = getSport(sport);
  if (!valid) {
    return NextResponse.json({ error: "Unknown sport", sport }, { status: 400 });
  }

  return NextResponse.json(
    { rows: [] },
    { headers: { "cache-control": "no-store, no-cache" } }
  );
}
