import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY,
  edgeBoardAssembleBootstrapScript,
  edgeBoardAssembleHref,
  takeEdgeBoardAssembleBootstrap,
} from "@/lib/edge-board-assemble-href";

const webRoot = path.join(__dirname, "../..");

describe("Edge Board assemble href + early bootstrap (#12 GO-1)", () => {
  it("builds stable assemble hrefs (NFL slate / CFB week)", () => {
    expect(edgeBoardAssembleHref({ sportKey: "nfl", slate: "week1" })).toBe(
      "/api/edge-board/nfl/assemble?slate=week1",
    );
    expect(edgeBoardAssembleHref({ sportKey: "nfl", slate: "full" })).toBe(
      "/api/edge-board/nfl/assemble?slate=full",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 1 })).toBe(
      "/api/edge-board/cfb/assemble?week=1",
    );
    expect(edgeBoardAssembleHref({ sportKey: "cfb", cfbWeek: 0 })).toBe(
      "/api/edge-board/cfb/assemble?week=0",
    );
    expect(edgeBoardAssembleHref({ sportKey: "mlb" })).toBe(
      "/api/edge-board/mlb/assemble",
    );
  });

  it("bootstrap script is idempotent and JSON-escapes href", () => {
    const href = "/api/edge-board/nfl/assemble?slate=week1";
    const script = edgeBoardAssembleBootstrapScript(href);
    expect(script).toContain(EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY);
    expect(script).toContain(JSON.stringify(href));
    expect(script).toContain('credentials:"same-origin"');
    expect(script).toContain("fetch(u,");
    expect(script).not.toMatch(/cache:\s*["']no-store["']/);
  });

  it("takeEdgeBoardAssembleBootstrap consumes once", async () => {
    const href = "/api/edge-board/nfl/assemble?slate=week1";
    const pending = Promise.resolve(new Response("{}", { status: 200 }));
    (
      window as Window & {
        [EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY]?: Record<string, Promise<Response>>;
      }
    )[EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY] = { [href]: pending };

    expect(takeEdgeBoardAssembleBootstrap(href)).toBe(pending);
    expect(takeEdgeBoardAssembleBootstrap(href)).toBeNull();
  });

  it("SSR page boots assemble without awaiting model-service", () => {
    const page = readFileSync(
      path.join(webRoot, "app/edge-board/[sport]/page.tsx"),
      "utf8",
    );
    expect(page).toContain("edgeBoardAssembleBootstrapScript");
    expect(page).toContain("edgeBoardAssembleHref");
    expect(page).toContain('rel="preload"');
    expect(page).toContain('as="fetch"');
    expect(page).not.toContain("loadAssembledEdgeBoardRows");
    expect(page).not.toMatch(/await\s+loadAssembled/);
    expect(page).not.toMatch(/\blinesAsOf\b/);
  });

  it("client prefers bootstrap and does not use cache:no-store", () => {
    const client = readFileSync(
      path.join(webRoot, "components/EdgeBoardSportClient.tsx"),
      "utf8",
    );
    expect(client).toContain("takeEdgeBoardAssembleBootstrap");
    expect(client).toContain("edgeBoardAssembleHref");
    expect(client).not.toMatch(/cache:\s*["']no-store["']/);
    expect(client).toContain('data-testid="edge-board-loading"');
    expect(client).toContain("Loading board…");
  });

  it("NFL assemble route honors requested slate (week1 ≠ full enrich)", () => {
    const assemble = readFileSync(
      path.join(webRoot, "app/api/edge-board/[sport]/assemble/route.ts"),
      "utf8",
    );
    expect(assemble).toContain("slate,");
    expect(assemble).toContain('slate === "full" ? gameCount(assembled) : 0');
    expect(assemble).not.toMatch(
      /loadAssembledEdgeBoardRows\("nfl",\s*\{\s*slate:\s*"full"/,
    );
  });
});

describe("takeEdgeBoardAssembleBootstrap (jsdom window)", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      [EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY]: undefined,
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns null when bag missing", () => {
    expect(
      takeEdgeBoardAssembleBootstrap(
        "/api/edge-board/nfl/assemble?slate=week1",
      ),
    ).toBeNull();
  });
});
