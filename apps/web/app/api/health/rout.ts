import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const now = new Date().toISOString();
  const dbOk = await prisma.$queryRaw`SELECT 1`;
  return NextResponse.json({ ok: true, now, dbOk });
}