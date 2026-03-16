// apps/web/proxy.ts
// Next.js 16: proxy replaces middleware. Single runtime gate for security headers.
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { addSecurityHeaders } from "@/lib/security/headers";

export function proxy(_request: NextRequest) {
  const response = NextResponse.next();
  return addSecurityHeaders(response);
}

export const config = {
  matcher: [
    // Match all request paths except static files and Next.js internals.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:ico|png|jpg|jpeg|gif|webp|svg|woff2?)$).*)",
  ],
};

