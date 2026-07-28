// apps/web/lib/security/headers.ts
import { NextResponse } from "next/server";

export function addSecurityHeaders(response: NextResponse) {
  const headers = response.headers;

  // Content Security Policy
  headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Next.js requires unsafe-eval in dev
      "style-src 'self' 'unsafe-inline'", // Tailwind requires unsafe-inline
      "img-src 'self' data: https:",
      "font-src 'self' data:",
      "connect-src 'self' https:",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  );

  // X-Frame-Options
  headers.set("X-Frame-Options", "DENY");

  // X-Content-Type-Options
  headers.set("X-Content-Type-Options", "nosniff");

  // Referrer-Policy
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  // Permissions-Policy
  headers.set(
    "Permissions-Policy",
    ["camera=()", "microphone=()", "geolocation=()", "interest-cohort=()"].join(
      ", ",
    ),
  );

  // Strict-Transport-Security (HSTS) - only in production
  if (process.env.NODE_ENV === "production") {
    headers.set(
      "Strict-Transport-Security",
      "max-age=31536000; includeSubDomains; preload",
    );
  }

  return response;
}
