/**
 * Edge Board assemble URL + early bootstrap (#12 GO-1).
 *
 * SSR must not await assemble (Alex waterfall). Bootstrap starts the same
 * page-data GET during HTML parse so COLD hydrate is not a second waterfall.
 * Honesty unchanged: Loading / as-of unavailable until assemble returns.
 */

export type EdgeBoardAssembleHrefInput = {
  sportKey: string;
  slate?: "week1" | "full";
  cfbWeek?: 0 | 1;
};

/** Relative assemble href matching EdgeBoardSportClient fetch. */
export function edgeBoardAssembleHref(
  input: EdgeBoardAssembleHrefInput,
): string {
  const sport = (input.sportKey || "ncaam").toLowerCase();
  const qs = new URLSearchParams();
  if (sport === "nfl")
    qs.set("slate", input.slate === "full" ? "full" : "week1");
  if (sport === "cfb") qs.set("week", String(input.cfbWeek === 0 ? 0 : 1));
  const q = qs.toString();
  return `/api/edge-board/${sport}/assemble${q ? `?${q}` : ""}`;
}

/** window bag key — one in-flight Response promise per href. */
export const EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY = "__KOS_EB_ASSEMBLE__";

export type EdgeBoardAssembleBootstrapBag = Record<
  string,
  Promise<Response> | undefined
>;

declare global {
  interface Window {
    [EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY]?: EdgeBoardAssembleBootstrapBag;
  }
}

/**
 * Inline script body: kick assemble fetch ASAP (same credentials/headers as client).
 * Idempotent per href. CSP allows unsafe-inline on www.
 */
export function edgeBoardAssembleBootstrapScript(href: string): string {
  const key = EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY;
  // JSON.stringify for href — no user-controlled HTML injection.
  return (
    `window.${key}=window.${key}||{};` +
    `var u=${JSON.stringify(href)};` +
    `if(!window.${key}[u]){` +
    `window.${key}[u]=fetch(u,{credentials:"same-origin",headers:{accept:"application/json"}});` +
    `}`
  );
}

/**
 * Take (and clear) an SSR-started assemble promise for this href.
 * Returns null when bootstrap missing — client falls back to its own fetch.
 */
export function takeEdgeBoardAssembleBootstrap(
  href: string,
): Promise<Response> | null {
  if (typeof window === "undefined") return null;
  const bag = window[EDGE_BOARD_ASSEMBLE_BOOTSTRAP_KEY];
  if (!bag) return null;
  const pending = bag[href];
  if (!pending) return null;
  delete bag[href];
  return pending;
}
