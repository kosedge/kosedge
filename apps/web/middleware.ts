import { NextResponse } from "next/server";
import { addSecurityHeaders } from "@/lib/security/headers";

/**
 * Single runtime gate: applies security headers to every response.
 * No auth or Pro gating here; that stays in layouts/pages.
 */
export function middleware(request: Request) {
  const response = NextResponse.next();
  return addSecurityHeaders(response);
}

export const config = {
  matcher: [
    /*
     * Match all request paths except static files and Next.js internals.
     * Omit _next/static, _next/image, favicon, and public assets.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:ico|png|jpg|jpeg|gif|webp|svg|woff2?)$).*)",
  ],
};
