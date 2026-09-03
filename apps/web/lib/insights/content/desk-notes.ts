import type { InsightArticle } from "../types";

/**
 * Weekly desk notes — dated, sport-tagged when relevant.
 * Free: limited teasers / open notes. Pro: full set + archive.
 *
 * Scaffold: thin but real. Expand as the desk ships weekly.
 */
export const DESK_NOTES: InsightArticle[] = [
  {
    slug: "nfl-week-premarket-disagreement",
    kind: "desk-note",
    title: "NFL: Where Market and Fair Still Disagree",
    updatedAt: "2026-08-04",
    tier: "free",
    sports: ["nfl"],
    tags: ["market", "process"],
    bottomLine:
      "A few early NFL numbers are already past our fair; a few still sit soft. The job this week is disagreement — not a full card.",
    keyPoints: [
      "Prioritize spots where KEI and best available still diverge after juice.",
      'Ignore "must bet" narratives on chalk that already moved through fair.',
      "Empty sides of the slate are fine — see No Forced Action.",
    ],
    teaser:
      "Early NFL board vs desk fair: which sides still have daylight, and which are already cooked.",
    sections: [
      {
        heading: "How we're reading the board",
        blocks: [
          "Open the Edge Board with NFL filtered. We're looking for model/KEI vs best gaps that clear threshold — not for stories about public teams.",
          'If the market has already steamed through our number, that is information. Respect it; don\'t chase a worse price to be "on" a side.',
        ],
      },
      {
        heading: "Process note",
        blocks: [
          'Make the number first, then compare. If you find yourself justifying a play because the side "feels live," step back to Threshold Discipline.',
        ],
      },
    ],
    whatToDo: [
      {
        text: "Scan NFL Edge Board for open vs best and fair disagreement.",
        link: { label: "NFL Edge Board", href: "/edge-board/nfl" },
      },
      {
        text: "Cross-check KEI for the same slate.",
        link: { label: "NFL KEI Lines", href: "/pro/nfl/fair-lines" },
      },
      {
        text: "Refresh on threshold rules before sizing.",
        link: {
          label: "Threshold Discipline",
          href: "/insights/doctrine/threshold-discipline",
        },
      },
    ],
  },
  {
    slug: "cfb-survivor-trap-spots",
    kind: "desk-note",
    title: "CFB: Survivor Trap Spots on the Chalk",
    updatedAt: "2026-08-05",
    tier: "free",
    sports: ["cfb"],
    tags: ["survivor", "trap"],
    bottomLine:
      'The chalkiest CFB survivor names are where public tickets cluster. Trap risk is about price, volatility, and correlated fade — not about "who is better."',
    keyPoints: [
      "Survivor is a survival problem, not a straight-up handicap problem.",
      'Trap spots often look "safe" at the wrong number.',
      "Passing a week (or holding a landmine) beats forcing a popular name.",
    ],
    teaser:
      "Which CFB chalk looks like a survivor magnet — and why the desk is wary.",
    sections: [
      {
        heading: "What makes a trap",
        blocks: [
          [
            "Public concentration on one side",
            "Volatility that doesn't show in the moneyline alone",
            "A number that already prices out the easy narrative",
          ],
          "We're not publishing a pick sheet here. We're publishing how the desk thinks about forced-action weeks.",
        ],
      },
      {
        heading: "Tie-in to doctrine",
        blocks: [
          "No Forced Action applies harder in survivor than anywhere else. An empty or contrarian stance that follows process beats a ticket full of consensus chalk.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "Read No Forced Action before locking a consensus name.",
        link: {
          label: "No Forced Action",
          href: "/insights/doctrine/no-forced-action",
        },
      },
      {
        text: "Price the game on CFB Edge Board — don't survivor off vibes.",
        link: { label: "CFB Edge Board", href: "/edge-board/cfb?week=1" },
      },
    ],
  },
  {
    slug: "mlb-injury-reprice-logic",
    kind: "desk-note",
    title: "MLB: Injury Reprice Without Chasing Steam",
    updatedAt: "2026-08-06",
    tier: "pro",
    sports: ["mlb"],
    tags: ["injury", "reprice"],
    bottomLine:
      "Starter and lineup news only moves KEI when the source clears the information tier — and only becomes a bet if the new fair still disagrees with the market.",
    keyPoints: [
      "Official lineup/IL news > beat confirmation > timeline rumors.",
      "Ask how much the market already moved before you buy.",
      "Simulation → reprice → threshold. Skip any step and you're gambling the headline.",
    ],
    teaser:
      "Pro desk: how we're repricing MLB after late pitcher/lineup information — and when we pass.",
    sections: [
      {
        heading: "Reprice checklist",
        blocks: [
          [
            "Confirm information tier",
            "Update fair / KEI",
            "Compare to best available after the move",
            "Apply threshold — pass if daylight is gone",
          ],
          "Steam without a fair update is how you buy the wrong side of the news.",
        ],
      },
      {
        heading: "Why this stays Pro",
        blocks: [
          'The weekly reprice diary is ongoing desk work — deeper "why this number" than the public doctrine. Doctrine stays free; the live application is the Pro layer.',
        ],
      },
    ],
    whatToDo: [
      {
        text: "After news, re-check MLB KEI before touching a ticket.",
        link: { label: "MLB KEI Lines", href: "/pro/kei-lines/mlb" },
      },
      {
        text: "Refresh Information Has Tiers.",
        link: {
          label: "Information Has Tiers",
          href: "/insights/doctrine/information-has-tiers",
        },
      },
      {
        text: "Use MLB Edge Board for best/open context post-move.",
        link: { label: "MLB Edge Board", href: "/edge-board/mlb" },
      },
    ],
  },
  {
    slug: "nba-process-note-thin-slate",
    kind: "desk-note",
    title: "NBA: Thin Slate, Full Process",
    updatedAt: "2026-08-07",
    tier: "pro",
    sports: ["nba"],
    tags: ["process"],
    bottomLine:
      "When the NBA board is quiet, we still run the process — and we still leave blank. Rest news and totals juice are where soft money forces action.",
    keyPoints: [
      "Quiet boards are a feature of threshold discipline.",
      "Totals and alternate markets still need the same fair-first pass.",
      "Pro notes document the pass, not just the plays.",
    ],
    teaser:
      "Pro desk: why a quiet NBA card is still a full workday — and what we're watching anyway.",
    sections: [
      {
        heading: "What we still check",
        blocks: [
          "Rest / schedule spots, confirmed outs, and whether KEI vs market gap clears juice-adjusted threshold.",
          "If nothing clears, the note is the work product. That is intentional.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "Confirm the board yourself on NBA Edge Board.",
        link: { label: "NBA Edge Board", href: "/edge-board/nba" },
      },
      {
        text: "Doctrine reminder: empty slate is allowed.",
        link: {
          label: "No Forced Action",
          href: "/insights/doctrine/no-forced-action",
        },
      },
    ],
  },
  {
    slug: "cbb-market-vs-power",
    kind: "desk-note",
    title: "CBB: Power vs Market Early Tells",
    updatedAt: "2026-08-03",
    tier: "pro",
    sports: ["ncaam"],
    tags: ["market", "power"],
    bottomLine:
      "When power ratings and the board diverge early, we ask whether information or inefficiency is driving it — before we call it edge.",
    keyPoints: [
      "Power is a research input, not a bet.",
      "Market may be ahead on lineup/tempo information.",
      "Edge still requires KEI vs price after the check.",
    ],
    teaser:
      "Pro desk: early CBB spots where power and market disagree — and how we adjudicate.",
    sections: [
      {
        heading: "Adjudication order",
        blocks: [
          "Make number → check information tiers → KEI reprice → market compare → threshold.",
          "Power ratings alone never clear a bet.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "Open CBB power for context, then price on the board.",
        link: {
          label: "CBB Power Ratings",
          href: "/pro/power-ratings/ncaam",
        },
      },
      {
        text: "CBB Edge Board for live disagreement.",
        link: { label: "CBB Edge Board", href: "/edge-board/ncaam" },
      },
    ],
  },
];

/** Notes for the current ISO week window (last 14 days as "this week" shelf). */
export function getRecentDeskNotes(withinDays = 14): InsightArticle[] {
  const cutoff = Date.now() - withinDays * 24 * 60 * 60 * 1000;
  return getAllDeskNotes().filter((n) => {
    const t = Date.parse(n.updatedAt);
    return Number.isFinite(t) && t >= cutoff;
  });
}

export function getAllDeskNotes(): InsightArticle[] {
  return [...DESK_NOTES].sort((a, b) =>
    a.updatedAt < b.updatedAt ? 1 : a.updatedAt > b.updatedAt ? -1 : 0,
  );
}

export function getDeskNoteBySlug(slug: string): InsightArticle | null {
  return DESK_NOTES.find((n) => n.slug === slug) ?? null;
}

/** Free open notes (full body for non-Pro). Limited set. */
export function getFreeDeskNotes(): InsightArticle[] {
  return getAllDeskNotes().filter((n) => n.tier === "free");
}

export function getDeskNotesBySport(sport: string): InsightArticle[] {
  return getAllDeskNotes().filter((n) => n.sports?.includes(sport as never));
}
