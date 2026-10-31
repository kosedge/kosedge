import { beforeEach, describe, expect, it, vi } from "vitest";

const redirect = vi.fn((url: string) => {
  throw new Error(`NEXT_REDIRECT ${url}`);
});
const isOpenAccessPreviewEnabled = vi.fn();
const isProUser = vi.fn();

vi.mock("next/navigation", () => ({
  redirect: (url: string) => redirect(url),
}));

vi.mock("@/lib/auth/pro", () => ({
  isOpenAccessPreviewEnabled: () => isOpenAccessPreviewEnabled(),
  isProUser: () => isProUser(),
}));

const { default: PricingPage } = await import("@/app/pricing/page");

describe("pricing page preview behavior (A6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("with preview false, entitled users redirect to /pro/welcome", async () => {
    isOpenAccessPreviewEnabled.mockReturnValue(false);
    isProUser.mockResolvedValue(true);
    await expect(PricingPage()).rejects.toThrow(
      "NEXT_REDIRECT /pro/welcome",
    );
  });

  it("with preview unset/false, non-entitled users stay on pricing", async () => {
    isOpenAccessPreviewEnabled.mockReturnValue(false);
    isProUser.mockResolvedValue(false);
    const el = await PricingPage();
    expect(el).toBeTruthy();
    expect(redirect).not.toHaveBeenCalled();
  });

  it("with preview true, entitled users are not redirected (launch override)", async () => {
    isOpenAccessPreviewEnabled.mockReturnValue(true);
    isProUser.mockResolvedValue(true);
    const el = await PricingPage();
    expect(el).toBeTruthy();
    expect(redirect).not.toHaveBeenCalled();
  });
});
