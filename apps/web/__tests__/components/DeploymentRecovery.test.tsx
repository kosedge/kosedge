import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { DeploymentRecovery } from "@/components/DeploymentRecovery";

describe("DeploymentRecovery", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.stubGlobal("location", { ...window.location, reload: vi.fn() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reloads once on ChunkLoadError", () => {
    render(<DeploymentRecovery />);
    window.dispatchEvent(
      new ErrorEvent("error", {
        message: "ChunkLoadError: Loading chunk 123 failed.",
        error: new Error("ChunkLoadError: Loading chunk 123 failed."),
      }),
    );
    expect(window.location.reload).toHaveBeenCalledTimes(1);
  });

  it("reloads once on failed dynamic import rejection", () => {
    render(<DeploymentRecovery />);
    const reason = new Error("Failed to fetch dynamically imported module");
    // jsdom may not implement PromiseRejectionEvent — synthesize the shape.
    const event = new Event("unhandledrejection") as Event & {
      reason: unknown;
      preventDefault: () => void;
    };
    Object.defineProperty(event, "reason", { value: reason });
    event.preventDefault = vi.fn();
    window.dispatchEvent(event);
    expect(window.location.reload).toHaveBeenCalledTimes(1);
  });

  it("does not loop-reload within the cooldown window", () => {
    render(<DeploymentRecovery />);
    const msg = "Loading chunk abc-def failed";
    window.dispatchEvent(new ErrorEvent("error", { message: msg }));
    window.dispatchEvent(new ErrorEvent("error", { message: msg }));
    expect(window.location.reload).toHaveBeenCalledTimes(1);
  });
});
