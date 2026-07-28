import { describe, expect, it } from "vitest";
import { nflCandidateTag, nflPublishTag } from "@/lib/nfl-publish-policy";

describe("nfl-publish-policy", () => {
  it("defaults to PASS outside productive bands", () => {
    expect(nflCandidateTag("spread", 1.5)).toBe("PASS");
    expect(nflCandidateTag("total", 3.5)).toBe("PASS");
    expect(nflCandidateTag("total", 2.0)).toBe("PASS");
  });

  it("allows PLAY only in cleared bands", () => {
    expect(nflCandidateTag("spread", 2.5)).toBe("PLAY");
    expect(nflCandidateTag("total", 2.7)).toBe("PLAY");
  });

  it("forces PASS when product gate is RED", () => {
    const out = nflPublishTag("spread", 4.0, "RED");
    expect(out.tag).toBe("PASS");
    expect(out.stakeEligible).toBe(false);
  });

  it("marks PLAY stake-eligible under YELLOW/GREEN product gate", () => {
    const out = nflPublishTag("spread", 3.0, "YELLOW");
    expect(out.tag).toBe("PLAY");
    expect(out.stakeEligible).toBe(true);
  });
});
