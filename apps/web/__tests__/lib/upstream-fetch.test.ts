import { afterEach, describe, expect, it, vi } from "vitest";
import {
  UpstreamTimeoutError,
  upstreamFetch,
} from "@/lib/upstream-fetch";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("upstreamFetch", () => {
  it("returns a successful response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("ok", { status: 200 })),
    );
    const res = await upstreamFetch("https://example.test/health", {
      timeoutMs: 1000,
    });
    expect(res.status).toBe(200);
    expect(await res.text()).toBe("ok");
  });

  it("aborts and throws UpstreamTimeoutError when the upstream never resolves", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            const signal = init?.signal;
            if (!signal) return;
            signal.addEventListener("abort", () => {
              reject(new DOMException("Aborted", "AbortError"));
            });
          }),
      ),
    );

    const pending = upstreamFetch("https://example.test/slow", {
      timeoutMs: 50,
    });
    const assertion = expect(pending).rejects.toBeInstanceOf(
      UpstreamTimeoutError,
    );
    await vi.advanceTimersByTimeAsync(60);
    await assertion;
  });
});
