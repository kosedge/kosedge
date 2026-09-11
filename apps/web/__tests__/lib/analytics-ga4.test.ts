import { NextResponse } from "next/server";
import { describe, expect, it } from "vitest";
import { GA4_MEASUREMENT_ID } from "@/lib/analytics/ga4";
import { addSecurityHeaders } from "@/lib/security/headers";

describe("GA4 install", () => {
  it("uses the single production measurement ID", () => {
    expect(GA4_MEASUREMENT_ID).toBe("G-W8W90FWPT7");
  });

  it("allows GA4 gtag.js hosts in the script CSP", () => {
    const response = addSecurityHeaders(NextResponse.next());
    const csp = response.headers.get("Content-Security-Policy") ?? "";
    const scriptSrc = csp
      .split(";")
      .find((part) => part.trim().startsWith("script-src"));
    expect(scriptSrc).toContain("https://www.googletagmanager.com");
    expect(scriptSrc).toContain("https://www.google-analytics.com");
  });
});
