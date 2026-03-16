import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiError, handleApiError } from "@/lib/api/error-handler";
import { ZodError } from "zod";

vi.mock("@/lib/logger", () => ({
  logError: vi.fn(),
}));

vi.mock("@/lib/config/env", () => ({
  env: { NODE_ENV: "test" },
}));

describe("lib/api/error-handler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("handleApiError", () => {
    it("returns correct status and body for ApiError", async () => {
      const err = new ApiError(404, "Not found", "NOT_FOUND");
      const res = handleApiError(err);
      expect(res.status).toBe(404);
      const body = await res.json();
      expect(body).toMatchObject({ error: "Not found", code: "NOT_FOUND" });
    });

    it("includes details for ApiError when provided", async () => {
      const err = new ApiError(400, "Invalid", "INVALID", { field: "email" });
      const res = handleApiError(err);
      const body = await res.json();
      expect(body).toMatchObject({ error: "Invalid", code: "INVALID", details: { field: "email" } });
    });

    it("returns 400 and VALIDATION_ERROR for ZodError", async () => {
      const err = new ZodError([
        { path: ["email"], message: "Invalid email", code: "invalid_string" },
      ]);
      const res = handleApiError(err);
      expect(res.status).toBe(400);
      const body = await res.json();
      expect(body).toMatchObject({ error: "Validation failed", code: "VALIDATION_ERROR" });
      expect(Array.isArray(body.issues)).toBe(true);
    });

    it("returns 500 for generic Error", async () => {
      const res = handleApiError(new Error("Something broke"));
      expect(res.status).toBe(500);
      const body = await res.json();
      expect(body).toMatchObject({ code: "INTERNAL_ERROR" });
      expect(typeof body.error).toBe("string");
    });

    it("returns 500 for unknown throwable", async () => {
      const res = handleApiError("string error");
      expect(res.status).toBe(500);
      const body = await res.json();
      expect(body).toMatchObject({ error: "An unknown error occurred", code: "UNKNOWN_ERROR" });
    });
  });
});
