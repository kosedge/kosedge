import { describe, it, expect } from "vitest";
import { GET } from "@/app/api/live-line/route";

describe("GET /api/live-line", () => {
  it("returns 200 with expected shape for valid query", async () => {
    const url = "http://localhost/api/live-line?pregameSpread=-5&homeScore=30&awayScore=28&minutesRemaining=10";
    const req = new Request(url);
    const res = await GET(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(typeof data.currentMargin).toBe("number");
    expect(typeof data.modelLiveSpreadHome).toBe("number");
    expect(data.edgeVsMarket === null || typeof data.edgeVsMarket === "number").toBe(true);
  });

  it("returns 200 with edgeVsMarket when marketSpread provided", async () => {
    const url =
      "http://localhost/api/live-line?pregameSpread=-5&homeScore=30&awayScore=28&minutesRemaining=10&marketSpread=-4";
    const req = new Request(url);
    const res = await GET(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(typeof data.edgeVsMarket).toBe("number");
  });

  it("returns 400 with VALIDATION_ERROR for missing params", async () => {
    const req = new Request("http://localhost/api/live-line");
    const res = await GET(req);
    const data = await res.json();

    expect(res.status).toBe(400);
    expect(data).toMatchObject({ error: expect.any(String), code: "VALIDATION_ERROR" });
  });

  it("returns 400 for invalid numeric params", async () => {
    const url =
      "http://localhost/api/live-line?pregameSpread=foo&homeScore=30&awayScore=28&minutesRemaining=10";
    const req = new Request(url);
    const res = await GET(req);
    const data = await res.json();

    expect(res.status).toBe(400);
    expect(data.code).toBe("VALIDATION_ERROR");
  });
});
