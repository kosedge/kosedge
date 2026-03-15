/**
 * Standard API response helpers for consistent JSON shape and status codes.
 */
import { NextResponse } from "next/server";

export type JsonErrorBody = { error: string; code?: string };

export function jsonError(
  status: number,
  message: string,
  options?: { code?: string }
): NextResponse<JsonErrorBody> {
  const body: JsonErrorBody = { error: message };
  if (options?.code) body.code = options.code;
  return NextResponse.json(body, { status });
}

export function jsonOk<T>(data: T, init?: ResponseInit): NextResponse<T> {
  return NextResponse.json(data, init);
}
