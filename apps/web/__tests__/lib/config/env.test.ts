// apps/web/__tests__/lib/config/env.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("Environment Configuration", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("should validate required environment variables", async () => {
    process.env.MODEL_SERVICE_URL = "http://localhost:8000";
    process.env.DATABASE_URL = "postgresql://test:test@localhost:5432/test";

    const { env } = await import("@/lib/config/env");

    expect(env.MODEL_SERVICE_URL).toBe("http://localhost:8000");
    expect(env.DATABASE_URL).toBe("postgresql://test:test@localhost:5432/test");
  });

  it("should accept optional AUTH_SECRET", async () => {
    process.env.MODEL_SERVICE_URL = "http://localhost:8000";
    process.env.DATABASE_URL = "postgresql://test:test@localhost:5432/test";
    process.env.AUTH_SECRET = "test-secret-key-at-least-32-characters-long";

    const { env } = await import("@/lib/config/env");

    expect(env.AUTH_SECRET).toBe("test-secret-key-at-least-32-characters-long");
  });

  it("should throw error for invalid URL", async () => {
    process.env.MODEL_SERVICE_URL = "not-a-valid-url";
    process.env.DATABASE_URL = "postgresql://test:test@localhost:5432/test";

    await expect(async () => {
      await import("@/lib/config/env");
    }).rejects.toThrow();
  });
});
