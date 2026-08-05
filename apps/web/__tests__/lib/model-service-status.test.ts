import { describe, expect, it } from "vitest";
import {
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

  it("shows when there is no content and no honest empty status", () => {
    expect(
      shouldShowModelUnreachableBanner({
        error: "Model service returned 503.",
        hasContent: false,
      }),
    ).toBe(true);
  });
});

describe("modelUnreachableCopy", () => {
  it("explains misconfiguration distinctly", () => {
    expect(
      modelUnreachableCopy("MODEL_SERVICE_URL is not configured."),
    ).toContain("not configured");
  });
});
