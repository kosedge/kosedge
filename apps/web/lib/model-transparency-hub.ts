/**
 * Copy for /pro/model-transparency — the one product-surface explanation hub.
 * Keep boards clean; this file is the SoT for Model / KEI / Edge language.
 */

export const MODEL_TRANSPARENCY_HREF = "/pro/model-transparency";
export const MODEL_TRANSPARENCY_TITLE = "Model Transparency";
export const MODEL_TRANSPARENCY_ONE_LINER =
  "How KosEdge model, handicap, and product surfaces work — in one place";

export const MODEL_TRANSPARENCY_CONTRACT = [
  {
    term: "Model",
    meaning:
      "Research fair — a pure sim / strength snapshot. It does not drive PLAY or LEAN on its own.",
  },
  {
    term: "KEI",
    meaning:
      "Final handicap. Model plus late information and reprice — desk factors such as injury, rest, weather, confirmation.",
  },
  {
    term: "Edge / Tag",
    meaning:
      "KEI versus the best available market only — never pure Model versus market for PLAY or LEAN.",
  },
  {
    term: "Estimates",
    meaning:
      "Numbers are research estimates, not instructions to bet and not a profitability promise.",
  },
] as const;

export const MODEL_TRANSPARENCY_SHOW = [
  "Honest empty, preseason, markets-only, and engine-warming states — no fake rows to fill a board.",
  "Thin sample and low-depth runs labeled as such.",
  "Fantasy: Model rank is projection order, not recommended pick order. ADP-aware advice lives on Builder and Mock.",
] as const;

export const MODEL_TRANSPARENCY_DONT = [
  "We do not invent KEI, copy books into KEI cells, or imply CLV from a short live sample.",
  "We do not sell locks, pick-service instructions, or a sure thing.",
] as const;

export type ModelTransparencyGlossaryEntry = {
  id: string;
  title: string;
  href?: string;
  lines: readonly string[];
};

export const MODEL_TRANSPARENCY_GLOSSARY: readonly ModelTransparencyGlossaryEntry[] =
  [
    {
      id: "desk-status",
      title: "Desk status (PRESEASON / data stale)",
      lines: [
        "PRESEASON / production no-go: PLAY stake tags and survivor locks stay research-only until readiness is go.",
        "data stale: boards may use the last owned snapshot; do not treat PLAY tags as live stakes until freshness recovers.",
        "Freshness and readiness probes still gate PLAY tags. Policy lives here — not on product boards.",
        "CLV Tracker and Performance remain the live / held-out accountability surfaces.",
      ],
    },
    {
      id: "edge-board",
      title: "Edge Board",
      href: "/edge-board/nfl",
      lines: [
        "The action board: KEI versus the best market on the slate.",
        "Tags (PASS / LEAN / PLAY) compare KEI to current books — never Model to market.",
        "Empty, markets-only, and warming states stay honest. Not a pick ticker.",
      ],
    },
    {
      id: "kei-lines",
      title: "KEI Lines",
      href: "/pro/nfl/fair-lines",
      lines: [
        "Published handicap after Model plus late information.",
        "The Model column is research fair and can differ from KEI.",
        "Edges and tags still use KEI versus market only.",
      ],
    },
    {
      id: "weekly-slate",
      title: "Weekly slate / matchups",
      href: "/pro/nfl/slate/today",
      lines: [
        "The week's games, matchup briefs, and slate snapshot.",
        "Not a second pricing engine — lines and tags still come from KEI versus market.",
      ],
    },
    {
      id: "survivor",
      title: "Survivor",
      href: "/pro/nfl/survivor",
      lines: [
        "Season-path planner: remaining teams, byes, and suggested paths.",
        "This week % on the desk is KEI SU win probability (same as Pick’em) when a fair line joins.",
        "Path / save / pick-now still use the season engine. Interactive runs are low-depth estimates.",
        "Packaged depth as-of is not a live injury feed. Path % is research, not a promise.",
      ],
    },
    {
      id: "fantasy",
      title: "Fantasy",
      href: "/pro/nfl/fantasy",
      lines: [
        "Draft board default is Value Δ + Wait/Take. Model rank is projection order, not pick order.",
        "Builder and Mock use the same projections with ADP-aware take / wait / reach advice.",
        "ADP source and freshness stay on the board. Missing K/DST stay empty until they exist.",
      ],
    },
    {
      id: "pickem",
      title: "Pick’em",
      href: "/pro/nfl/fantasy/pickem",
      lines: [
        "Two cards: ATS (default) and Straight up. Rank is 1–N, not a stake.",
        "ATS side is KEI vs the stake line (DK → FD → consensus). SU side is the KEI winner.",
        "PLAY / LEAN only change sort order. Research estimates, not a contest entry.",
      ],
    },
    {
      id: "game-boxes",
      title: "Game Boxes / Season Model",
      href: "/pro/nfl/model",
      lines: [
        "One production spine: player-game means for boxes; season totals are the sum of weeks.",
        "True PR, Game Boxes, and Survivor share that engine — not three stories.",
        "Research lock and path-count lineage live here — not in the page header.",
        "Preseason boards are labeled as such.",
      ],
    },
    {
      id: "power-ratings",
      title: "Power Ratings",
      href: "/pro/power-ratings/nfl",
      lines: [
        "Strength snapshot that feeds the model — not a bet card.",
        "Rank order is research, not a lock list.",
        "Current pin is Method B compressed strength; engine / run / path count live on Season Model, not on the ratings table.",
      ],
    },
    {
      id: "camp-desk",
      title: "Camp Desk / Injuries & News",
      href: "/pro/nfl/camp",
      lines: [
        "Camp Desk: dated KosEdge notes with citations — never a tweet mirror.",
        "Research beat, official, and sharp-capable desks; thin camp info stays Pass.",
        "Daily YYYY-MM-DD packages; Monday refreshes all 32 team previews (Date + Bottom line / What matters most).",
        "SoT flags queue the existing depth job — this page does not publish a new model run.",
        "Injuries & News is the feed when posted. Neither surface is a pricing engine.",
      ],
    },
    {
      id: "insights",
      title: "Insights / Doctrine",
      href: "/insights/doctrine",
      lines: [
        "Evergreen process writing — how the desk thinks, not live numbers.",
        "Methodology and About stay the public long-form. This hub is the product map.",
      ],
    },
    {
      id: "props",
      title: "Props",
      href: "/pro/nfl/props",
      lines: [
        "Weekly player means from the same production spine as fantasy.",
        "Edge versus market when a book is joined. No PLAY / LEAN stake tags.",
        "2026 preseason receiving grain is labeled. Not a profitability claim.",
      ],
    },
  ];

export const MODEL_TRANSPARENCY_FOOTER_LINKS = [
  { href: "/methodology", label: "Methodology" },
  { href: "/about", label: "About" },
  { href: "/disclaimer", label: "Disclaimer" },
] as const;

const FORBIDDEN_HUB_PHRASES = [
  /guaranteed edge/i,
  /lock of the (day|week)/i,
  /must bet/i,
  /can't lose/i,
] as const;

export function modelTransparencyHubCopy(): string {
  return [
    MODEL_TRANSPARENCY_TITLE,
    MODEL_TRANSPARENCY_ONE_LINER,
    ...MODEL_TRANSPARENCY_CONTRACT.map((row) => `${row.term} ${row.meaning}`),
    ...MODEL_TRANSPARENCY_SHOW,
    ...MODEL_TRANSPARENCY_DONT,
    ...MODEL_TRANSPARENCY_GLOSSARY.flatMap((entry) => [
      entry.title,
      ...entry.lines,
    ]),
  ].join("\n");
}

export function assertModelTransparencyHubSafe(
  copy = modelTransparencyHubCopy(),
) {
  for (const pattern of FORBIDDEN_HUB_PHRASES) {
    if (pattern.test(copy)) {
      throw new Error(`Hub copy contains forbidden phrase: ${pattern}`);
    }
  }
}
