import { beforeEach, describe, expect, it, vi } from "vitest";

const headersGet = vi.fn<(name: string) => string | null>();
const redirect = vi.fn((url: string) => {
  throw new Error(`NEXT_REDIRECT ${url}`);
});
const getProAccessState = vi.fn();

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => ({
    get: headersGet,
  })),
}));

vi.mock("next/navigation", () => ({
  redirect: (url: string) => redirect(url),
}));

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: () => getProAccessState(),
}));

const { default: ProRootLayout } = await import("@/app/(pro)/pro/layout");

describe("Pro layout redirects (A6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    headersGet.mockReturnValue("/pro/nfl/overview");
  });

  it("redirects unauthenticated users to sign-in", async () => {
    getProAccessState.mockResolvedValue("unauthenticated");
    await expect(ProRootLayout({ children: "desk" })).rejects.toThrow(
      "NEXT_REDIRECT /auth/signin?callbackUrl=/pro/welcome",
    );
  });

  it("redirects forbidden users to /pricing", async () => {
    getProAccessState.mockResolvedValue("forbidden");
    await expect(ProRootLayout({ children: "desk" })).rejects.toThrow(
      "NEXT_REDIRECT /pricing",
    );
  });

  it("renders children when authorized", async () => {
    getProAccessState.mockResolvedValue("authorized");
    const el = await ProRootLayout({ children: "desk" });
    expect(el).toBeTruthy();
    expect(redirect).not.toHaveBeenCalled();
  });

  it("leaves public Pro paths open without calling the gate", async () => {
    for (const path of [
      "/pro/nfl/launch-notes",
      "/pro/nfl/launch-notes/",
      "/pro/model-transparency",
    ]) {
      vi.clearAllMocks();
      headersGet.mockReturnValue(path);
      const el = await ProRootLayout({ children: "public" });
      expect(el).toBeTruthy();
      expect(getProAccessState).not.toHaveBeenCalled();
      expect(redirect).not.toHaveBeenCalled();
    }
  });
});
