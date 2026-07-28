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

    // Exhaust the auth write limiter (10 points)
    for (let i = 0; i < 10; i++) {
      const req = new NextRequest(base, {
        headers: { "x-forwarded-for": clientId },
      });
      const res = await rateLimit(req);
      expect(res).toBeNull();
    }

    // 11th request should be rate limited
    const req = new NextRequest(base, {
      headers: { "x-forwarded-for": clientId },
    });
    const res = await rateLimit(req);
    expect(res).not.toBeNull();
    expect(res!.status).toBe(429);
    const data = await res!.json();
    expect(data.code).toBe("RATE_LIMIT_EXCEEDED");
    expect(data.retryAfter).toBeDefined();
    expect(res!.headers.get("X-RateLimit-Limit")).toBe("10");
  });

  it("cannot bypass auth limiter by rotating Authorization header", async () => {
    const clientIp = "rate-limit-auth-header-rotation-" + Date.now();
    const base = "http://localhost/api/auth/signin";

    for (let i = 0; i < 10; i++) {
      const req = new NextRequest(base, {
        headers: {
          "x-forwarded-for": clientIp,
          authorization: `Bearer fake-token-${i}`,
        },
      });
      const res = await rateLimit(req);
      expect(res).toBeNull();
    }

    const req = new NextRequest(base, {
      headers: {
        "x-forwarded-for": clientIp,
        authorization: "Bearer totally-different-token",
      },
    });
    const res = await rateLimit(req);
    expect(res).not.toBeNull();
    expect(res!.status).toBe(429);
  });
});
