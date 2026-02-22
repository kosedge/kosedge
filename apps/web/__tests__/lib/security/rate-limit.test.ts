import { describe, it, expect } from "vitest";
import { rateLimit } from "@/lib/security/rate-limit";
import { NextRequest } from "next/server";

describe("rateLimit", () => {
  it("returns null for non-API paths (no rate limiting)", async () => {
    const req = new NextRequest("http://localhost/");
    const res = await rateLimit(req);
    expect(res).toBeNull();
  });

  it("allows first request to API path", async () => {
    const req = new NextRequest("http://localhost/api/ping", {
      headers: { "x-forwarded-for": "192.168.1.100" },
    });
    const res = await rateLimit(req);
    expect(res).toBeNull();
  });

  it("returns 429 when auth endpoint limit exceeded", async () => {
    const clientId = "rate-limit-test-auth-" + Date.now();
    const base = "http://localhost/api/auth/signin";

    // Exhaust the auth limiter (5 points)
    for (let i = 0; i < 5; i++) {
      const req = new NextRequest(base, {
        headers: { "x-forwarded-for": clientId },
      });
      const res = await rateLimit(req);
      expect(res).toBeNull();
    }

    // 6th request should be rate limited
    const req = new NextRequest(base, {
      headers: { "x-forwarded-for": clientId },
    });
    const res = await rateLimit(req);
    expect(res).not.toBeNull();
    expect(res!.status).toBe(429);
    const data = await res!.json();
    expect(data.code).toBe("RATE_LIMIT_EXCEEDED");
    expect(data.retryAfter).toBeDefined();
    expect(res!.headers.get("X-RateLimit-Limit")).toBe("5");
  });
});
