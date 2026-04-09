// apps/web/proxy.ts
// Next.js 16: middleware renamed to proxy. Rate limit API, add security headers.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { rateLimit } from "@/lib/security/rate-limit";
import { addSecurityHeaders } from "@/lib/security/headers";

export async function proxy(request: NextRequest) {
  // Rate limit all API routes (including /api/auth), then add security headers.
  const rateLimitResponse = await rateLimit(request);
  if (rateLimitResponse) {
    addSecurityHeaders(rateLimitResponse);
    return rateLimitResponse;
  }

  const response = NextResponse.next();
  addSecurityHeaders(response);
  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
