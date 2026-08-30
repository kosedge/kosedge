import { describe, expect, it } from "vitest";
import {
  MODEL_TRANSPARENCY_CONTRACT,
  MODEL_TRANSPARENCY_GLOSSARY,
  MODEL_TRANSPARENCY_HREF,
  MODEL_TRANSPARENCY_ONE_LINER,
  MODEL_TRANSPARENCY_SHOW,
  assertModelTransparencyHubSafe,
  modelTransparencyHubCopy,
} from "@/lib/model-transparency-hub";

const REQUIRED_GLOSSARY_IDS = [
  "desk-status",
  "edge-board",
  "kei-lines",
  "weekly-slate",
  "survivor",
  "fantasy",
  "game-boxes",
  "power-ratings",
  "camp-desk",
  "insights",
  "props",
] as const;

describe("model transparency hub", () => {
  it("owns the product URL and one-liner", () => {
    expect(MODEL_TRANSPARENCY_HREF).toBe("/pro/model-transparency");
    expect(MODEL_TRANSPARENCY_ONE_LINER).toMatch(/in one place/i);
  });

  it("states Model / KEI / Edge vs market / no profit promise", () => {
    const blob = MODEL_TRANSPARENCY_CONTRACT.map(
      (row) => `${row.term} ${row.meaning}`,
    ).join(" ");
    expect(blob).toMatch(/research fair/i);
    expect(blob).toMatch(/final handicap/i);
    expect(blob).toMatch(/never pure Model versus market/i);
    expect(blob).toMatch(/not a profitability promise/i);
  });

  it("separates Model rank from fantasy pick order", () => {
    expect(MODEL_TRANSPARENCY_SHOW.join(" ")).toMatch(
      /not recommended pick order/i,
    );
  });

  it("covers every required surface with short entries", () => {
    const ids = MODEL_TRANSPARENCY_GLOSSARY.map((entry) => entry.id);
    expect(ids).toEqual([...REQUIRED_GLOSSARY_IDS]);
    for (const entry of MODEL_TRANSPARENCY_GLOSSARY) {
      expect(entry.lines.length).toBeGreaterThanOrEqual(2);
      expect(entry.lines.length).toBeLessThanOrEqual(5);
    }
  });

  it("explains PRESEASON / data stale desk status without raw probe dumps", () => {
    const desk = MODEL_TRANSPARENCY_GLOSSARY.find(
      (e) => e.id === "desk-status",
    );
    expect(desk).toBeTruthy();
    const blob = desk!.lines.join(" ");
    expect(blob).toMatch(/PRESEASON/i);
    expect(blob).toMatch(/data stale/i);
    expect(blob).toMatch(/research-only/i);
    expect(blob).not.toMatch(/sample_size_ok/);
    expect(blob).not.toMatch(/schedules_scores:/);
  });

  it("does not sell guaranteed edge", () => {
    expect(() => assertModelTransparencyHubSafe()).not.toThrow();
    expect(modelTransparencyHubCopy()).not.toMatch(/guaranteed/i);
  });
});
