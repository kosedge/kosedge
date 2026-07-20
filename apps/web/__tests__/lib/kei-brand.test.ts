import { describe, expect, it } from "vitest";
import { getKeiCode, getKeiProductLabel } from "@/lib/kei-brand";

describe("kei-brand", () => {
  it("maps sports to KEI product codes", () => {
    expect(getKeiCode("ncaam")).toBe("KEICMB");
    expect(getKeiCode("nfl")).toBe("KEINFL");
    expect(getKeiCode("nba")).toBe("KEINBA");
  });

  it("labels KEI as Kos Edge Index", () => {
    expect(getKeiProductLabel("nfl")).toBe("KEINFL (Kos Edge Index)");
  });
});
