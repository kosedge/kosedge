import { describe, it, expect } from "vitest";
import { jsonError, jsonOk } from "@/lib/api/response";

describe("lib/api/response", () => {
  describe("jsonError", () => {
    it("returns correct status and body with message only", async () => {
      const res = jsonError(400, "Bad request");
      expect(res.status).toBe(400);
      expect(res.headers.get("content-type")).toContain("application/json");
      const body = await res.json();
      expect(body).toEqual({ error: "Bad request" });
    });

    it("includes code when provided", async () => {
      const res = jsonError(422, "Validation failed", { code: "VALIDATION_ERROR" });
      expect(res.status).toBe(422);
      const body = await res.json();
      expect(body).toEqual({ error: "Validation failed", code: "VALIDATION_ERROR" });
    });
  });

  describe("jsonOk", () => {
    it("returns 200 and serializes data", async () => {
      const res = jsonOk({ ok: true, ts: 123 });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body).toEqual({ ok: true, ts: 123 });
    });

    it("accepts init for status and headers", async () => {
      const res = jsonOk({ id: "1" }, { status: 201 });
      expect(res.status).toBe(201);
      const body = await res.json();
      expect(body).toEqual({ id: "1" });
    });
  });
});
