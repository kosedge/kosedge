import { describe, it, expect } from "vitest";
import { middleware } from "@/middleware";

describe("middleware security headers", () => {
  it("applies core security headers to responses", () => {
    const res = middleware(new Request("http://localhost/"));

    const csp = res.headers.get("content-security-policy");
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'self'");

    expect(res.headers.get("x-frame-options")).toBe("DENY");
    expect(res.headers.get("x-content-type-options")).toBe("nosniff");
    expect(res.headers.get("referrer-policy")).toBe("strict-origin-when-cross-origin");
    expect(res.headers.get("permissions-policy")).toBeTruthy();

    // In test environment, HSTS should not be set (NODE_ENV !== production)
    expect(res.headers.get("strict-transport-security")).toBeNull();
  });
});

