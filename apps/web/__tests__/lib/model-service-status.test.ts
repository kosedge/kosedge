import { describe, expect, it } from "vitest";
import {
  honestEmptySlateCopy,
  inferHonestEmptySlateStatus,
  isNflPreseasonDeskWindow,
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";

describe("shouldShowModelUnreachableBanner", () => {
  it("hides when content is present despite transport error", () => {
    expect(
      shouldShowModelUnreachableBanner({
        error: "Upstream timed out",
        hasContent: true,
      }),
    ).toBe(false);
  });

  it("hides honest empty slate statuses", () => {
    expect(
      shouldShowModelUnreachableBanner({
        error: "Model service unreachable.",
        slateStatus: "offseason_empty",
      }),
    ).toBe(false);
  });

  it("hides preseason transport failures when slate_status is honest empty", () => {
    expect(
      shouldShowModelUnreachableBanner({
        error: "Unable to reach model service.",
        slateStatus: "preseason_empty",
      }),
    ).toBe(false);
  });

  it("shows when there is no content and no honest empty status", () => {
    expect(
      shouldShowModelUnreachableBanner({
        error: "Model service returned 503.",
        hasContent: false,
      }),
    ).toBe(true);
  });
});

describe("inferHonestEmptySlateStatus", () => {
  it("does not mask August transport failures once REG Week 1 board is live", () => {
    const august = new Date("2026-08-05T12:00:00Z");
    expect(isNflPreseasonDeskWindow(august)).toBe(false);
    expect(
      inferHonestEmptySlateStatus({
        season: 2026,
        error: "Unable to reach model service.",
      }),
    ).toBeNull();
  });
});

describe("honestEmptySlateCopy", () => {
  it("uses a legitimate empty slate, not internal service language", () => {
    expect(honestEmptySlateCopy("preseason_empty")).toBe(
      "No games currently scheduled for this slate. Model lines will appear when they are available.",
    );
    expect(honestEmptySlateCopy("preseason_empty")).not.toMatch(
      /model service|fair-lines|token/i,
    );
  });
});

describe("modelUnreachableCopy", () => {
  it("never leaks env keys or service names to customers", () => {
    expect(modelUnreachableCopy("MODEL_SERVICE_URL is not configured.")).toBe(
      "Model data temporarily unavailable.",
    );
    expect(modelUnreachableCopy("Unable to reach model service.")).toBe(
      "Model data temporarily unavailable.",
    );
  });
});
