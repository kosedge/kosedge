import { describe, expect, it } from "vitest";
import { isPublicProPath } from "@/lib/pro-public-paths";

describe("isPublicProPath", () => {
  it("allows NFL desk notes without Pro wall", () => {
    expect(isPublicProPath("/pro/nfl/launch-notes")).toBe(true);
    expect(isPublicProPath("/pro/nfl/launch-notes/")).toBe(true);
    expect(isPublicProPath("/pro/model-transparency")).toBe(true);
  });

  it("does not open the rest of Pro", () => {
    expect(isPublicProPath("/pro/nfl/overview")).toBe(false);
    expect(isPublicProPath("/pro/nfl/edges")).toBe(false);
    expect(isPublicProPath(null)).toBe(false);
  });
});
