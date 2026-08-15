/**
 * Weekly `/props/board` is a Postgres box-sim path, not the season CSV.
 * Until that sim is rebuilt on the post-SoT (Walker/KC) + post-#226 shape,
 * do not render stale/wrong-role weekly rows. Season desks stay live.
 *
 * Flip to true only after box-sim materializer lineage matches the launch bundle.
 */
export const NFL_WEEKLY_PROPS_LIVE = false;

export const NFL_WEEKLY_PROPS_PATH_COHERENT: "yes" | "gated" =
  NFL_WEEKLY_PROPS_LIVE ? "yes" : "gated";

export const NFL_WEEKLY_PROPS_GATE_TITLE =
  "Weekly player props not live — season desk only";

export const NFL_WEEKLY_PROPS_GATE_BODY =
  "Week 1 player props are gated until the weekly box sim is rebuilt on the same depth and production path as season projections. Season totals, fantasy ranks, and Edge Board game lines stay on the desk.";
