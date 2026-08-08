import type { InsightArticle } from "../types";

/**
 * KosEdge doctrine library — evergreen house rules.
 * Mostly free. No public module numbers. Builds trust in the desk.
 */
export const DOCTRINE: InsightArticle[] = [
  {
    slug: "make-our-number-first",
    kind: "doctrine",
    title: "Make Our Number First",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["process"],
    bottomLine:
      "Independent fair comes before market respect. We price the game, then we look at the board — never the other way around.",
    keyPoints: [
      "Build a research fair before you open a sportsbook screen.",
      "Market price is information, not a starting point for your number.",
      "Respect the close; don't outsource your opinion to it.",
    ],
    sections: [
      {
        heading: "Why order matters",
        blocks: [
          "If you start from the market, you inherit its framing — juice, key numbers, and narrative already baked in. Your \"edge\" becomes a story about why the board is wrong instead of a measurement of where your fair disagrees.",
          "KosEdge starts with an independent number: power, matchup, distribution, and context. Only after that number exists do we compare to open, best, and close.",
        ],
      },
      {
        heading: "Market respect without market capture",
        blocks: [
          "Respecting the market means updating when new information arrives and tracking CLV as a diagnostic. It does not mean anchoring your fair to whatever opened at -3.",
          "When our fair and the board agree, that is not a failure — it is a pass. Disagreement is where the desk earns its keep.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "On Edge Board, read model / KEI reference against open and best — don't reverse-engineer a take from the market alone.",
        link: { label: "Edge Board", href: "/edge-board" },
      },
      {
        text: "Use KEI Lines as the desk's current fair snapshot by sport.",
        link: { label: "KEI Lines", href: "/pro/kei-lines" },
      },
    ],
  },
  {
    slug: "model-vs-kei-vs-market",
    kind: "doctrine",
    title: "Model vs KEI vs Market",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["process", "kei"],
    bottomLine:
      "Research fair, handicap reprice, edge only vs market. Three layers — don't collapse them into one number.",
    keyPoints: [
      "Model = research fair from simulation and structure.",
      "KEI = handicap reprice that folds in information the raw model may lag.",
      "Market = the price you can actually bet. Edge lives only here.",
    ],
    sections: [
      {
        heading: "Three layers, three jobs",
        blocks: [
          "The model answers: what does the distribution say before we argue with the board?",
          "KEI answers: after trusted information and desk handicap, what is our actionable fair?",
          "The market answers: what can we get paid at right now? Edge is KEI (or fair) versus that price — not versus a narrative, and not versus last week's close.",
        ],
      },
      {
        heading: "Where people get confused",
        blocks: [
          [
            "Treating model output as a bet slip",
            "Skipping KEI and calling every model/market gap \"edge\"",
            "Chasing steam without updating fair",
          ],
          "KosEdge keeps the layers visible so you can see whether a play is research disagreement, information reprice, or true market misprice.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "Compare KEI to open/best on the Edge Board before you size anything.",
        link: { label: "Edge Board", href: "/edge-board" },
      },
      {
        text: "Pull sport-level KEI when you want the full fair grid.",
        link: { label: "KEI Lines", href: "/pro/kei-lines" },
      },
    ],
  },
  {
    slug: "threshold-discipline",
    kind: "doctrine",
    title: "Threshold Discipline",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["process", "discipline"],
    bottomLine:
      "Pass is a position. There is no \"close enough.\" If it doesn't clear the threshold, it doesn't clear the board.",
    keyPoints: [
      "Edge is measurable: fair vs market, after juice.",
      "A fixed threshold beats vibes and exceptions.",
      "Fewer, cleaner bets beat a full card of almosts.",
    ],
    sections: [
      {
        heading: "Why thresholds exist",
        blocks: [
          "Without a cutoff, every interesting matchup becomes a bet. Interesting is not +EV. Thresholds turn handicapping into a filter: act only when the price mistake is large enough to survive variance, juice, and your own estimation error.",
          "\"Close enough\" is how bankrolls die — one soft play at a time, each justified by a story.",
        ],
      },
      {
        heading: "Pass is work",
        blocks: [
          "An empty ticket after a full slate review is a successful desk session. You paid attention, applied the rules, and declined to manufacture action.",
          "KosEdge is built to show disagreement and still let you walk. The product is the number — not a forced play count.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "On Edge Board, sort and scan for gaps that actually clear your bar — ignore the rest of the slate.",
        link: { label: "Edge Board", href: "/edge-board" },
      },
      {
        text: "Read No Forced Action when the slate looks thin.",
        link: {
          label: "No Forced Action",
          href: "/insights/doctrine/no-forced-action",
        },
      },
    ],
  },
  {
    slug: "clv-is-a-diagnostic",
    kind: "doctrine",
    title: "CLV Is a Diagnostic",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["clv", "process"],
    bottomLine:
      "Closing line value is a useful lie detector for process — not the whole religion. Beat the close on average; don't worship every tick.",
    keyPoints: [
      "CLV checks whether you bought a better number than the market's final opinion.",
      "Positive CLV with bad thresholds still loses money.",
      "Use CLV to audit timing and information quality, not to grade single bets.",
    ],
    sections: [
      {
        heading: "What CLV is good for",
        blocks: [
          "Over a sample, beating the close suggests your entries were early relative to information flow — or that you shopped better. That is process signal.",
          "CLV also exposes late chasing: if you consistently buy worse than close, your timing or discipline is broken even when short-term results look fine.",
        ],
      },
      {
        heading: "What CLV is not",
        blocks: [
          [
            "Not a substitute for edge thresholds",
            "Not proof a single win was \"sharp\"",
            "Not a reason to bet into a number that no longer clears fair",
          ],
          "KosEdge tracks CLV so you can tell the truth about process. The religion remains: fair number, threshold, price.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "Review open vs close and +EV-at-close distributions on the CLV Tracker.",
        link: { label: "CLV Tracker", href: "/pro/clv-tracker" },
      },
      {
        text: "Pair CLV review with Model Transparency — process audit, not scoreboard.",
        link: {
          label: "Model Transparency",
          href: "/pro/model-transparency",
        },
      },
    ],
  },
  {
    slug: "information-has-tiers",
    kind: "doctrine",
    title: "Information Has Tiers",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["process", "injury"],
    bottomLine:
      "Official > trusted beat/insider > noise. Reprice only when the information earns the right to move your number.",
    keyPoints: [
      "Not all \"news\" deserves a line move.",
      "Tier your sources before you tier your bets.",
      "Late noise is how recreational money buys the wrong side of steam.",
    ],
    sections: [
      {
        heading: "The hierarchy",
        blocks: [
          [
            "Official: team/league confirmation, inactive lists, confirmed starters",
            "Trusted beat / known insider with a track record",
            "Aggregator rumors, anonymous replies, vibe accounts",
          ],
          "Move KEI hard on tier-one. Soft-update or wait on tier-two. Ignore tier-three until it graduates.",
        ],
      },
      {
        heading: "Injury and reprice logic",
        blocks: [
          "The question is never \"is this player out?\" alone. It is: how much did the market already move, and does our fair still disagree after a disciplined reprice?",
          "Desk notes this week will call out trap spots where the public overreacts to a name while the number is already past fair.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "After news, re-check KEI vs best available — don't bet the headline.",
        link: { label: "KEI Lines", href: "/pro/kei-lines" },
      },
      {
        text: "Scan This Week for injury/reprice desk notes when the slate is live.",
        link: { label: "This Week", href: "/insights" },
      },
    ],
  },
  {
    slug: "price-matters",
    kind: "doctrine",
    title: "Price Matters",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["price", "execution"],
    bottomLine:
      "Key numbers, juice, and thresholds decide whether a \"good side\" is actually a good bet. Side without price is just a rooting interest.",
    keyPoints: [
      "Half-points and key numbers change EV more than most narratives.",
      "Juice is part of the price — always.",
      "Best number shopping is non-negotiable over a season.",
    ],
    sections: [
      {
        heading: "Key numbers and juice",
        blocks: [
          "In football, 3 and 7 are not decorations. Crossing a key number can flip a play from pass to act — or kill one that looked fine at a worse number.",
          "In every sport, -110 vs -105 is real money across a hundred bets. Ignoring juice is how \"small\" leaks compound.",
        ],
      },
      {
        heading: "Shop or subsidize the book",
        blocks: [
          "If you habitually take the first number you see, you are donating CLV and EV. KosEdge surfaces open vs best so the cost of laziness is visible.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "Use Edge Board open vs best columns before you commit.",
        link: { label: "Edge Board", href: "/edge-board" },
      },
      {
        text: "Check Market Dashboard for steam and key-number context.",
        link: { label: "Market Dashboard", href: "/pro/market" },
      },
    ],
  },
  {
    slug: "bankroll-and-variance",
    kind: "doctrine",
    title: "Bankroll and Variance",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["bankroll", "variance"],
    bottomLine:
      "Survive long enough for edge to show. Sizing and drawdown tolerance are part of the model — not an afterthought.",
    keyPoints: [
      "Real edge still loses in clusters.",
      "Flat or capped sizing beats ego ramps.",
      "If your bankroll can't survive a normal drawdown, you don't have a strategy.",
    ],
    sections: [
      {
        heading: "Variance is not a verdict",
        blocks: [
          "A 55% process can go cold for weeks. That is math, not betrayal. People who size like every week must \"win\" turn variance into ruin.",
          "KosEdge teaches long-game bankroll thinking so subscribers stay solvent — and subscribed — through normal noise.",
        ],
      },
      {
        heading: "Sizing rules of thumb",
        blocks: [
          [
            "Default flat or unit-capped until calibration is proven",
            "Never size up to \"get even\"",
            "Cap exposure per slate and per correlated cluster",
          ],
        ],
      },
    ],
    whatToDo: [
      {
        text: "Use Model Transparency and CLV to judge process over short P&L.",
        link: {
          label: "Model Transparency",
          href: "/pro/model-transparency",
        },
      },
      {
        text: "Pair with Process Over Outcomes when grading a losing week.",
        link: {
          label: "Process Over Outcomes",
          href: "/insights/doctrine/process-over-outcomes",
        },
      },
    ],
  },
  {
    slug: "no-forced-action",
    kind: "doctrine",
    title: "No Forced Action",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["discipline"],
    bottomLine:
      "An empty slate is allowed. The desk does not owe you a card. Manufactured bets are how edges disappear.",
    keyPoints: [
      "Action bias is a tax.",
      "Passing preserves bankroll and process integrity.",
      "Survivor and fantasy still require passes — traps love forced tickets.",
    ],
    sections: [
      {
        heading: "Why desks force action",
        blocks: [
          "Content pressure, dopamine, and \"I put in the work\" all push toward betting something. None of those are +EV.",
          "KosEdge would rather publish a thin This Week than invent edges that don't clear threshold.",
        ],
      },
      {
        heading: "Survivor and slate traps",
        blocks: [
          "Forced survivor picks and \"must-play\" narratives are where public money concentrates. Desk notes will flag trap spots — your job is still to pass when the number is wrong.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "If Edge Board is quiet, take the win and wait for disagreement.",
        link: { label: "Edge Board", href: "/edge-board" },
      },
      {
        text: "Read This Week for trap callouts — not a mandate to fill a card.",
        link: { label: "This Week", href: "/insights" },
      },
    ],
  },
  {
    slug: "process-over-outcomes",
    kind: "doctrine",
    title: "Process Over Outcomes",
    updatedAt: "2026-08-08",
    tier: "free",
    tags: ["process"],
    bottomLine:
      "Grade good bet / bad bet by price and process, not by the scoreboard. Results are lagged, noisy feedback.",
    keyPoints: [
      "A winning bad bet is still a bad bet.",
      "A losing good bet is still a good bet.",
      "Review rules: fair, threshold, information tier, execution price.",
    ],
    sections: [
      {
        heading: "The grading frame",
        blocks: [
          "Ask: Did we make our number first? Did information justify the reprice? Did the price clear threshold at the number we actually got? Did we size sanely?",
          "If yes — keep the process even when the game goes against you. If no — fix the leak even when you cashed.",
        ],
      },
      {
        heading: "Why this protects the desk",
        blocks: [
          "Outcome-chasing rewrites rules after every Sunday. Process grading keeps the house rules stable so sample size can do its job.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "Audit entries with CLV and open/close — not just wins and losses.",
        link: { label: "CLV Tracker", href: "/pro/clv-tracker" },
      },
      {
        text: "Use weekly desk notes as process context, not as a pick sheet.",
        link: { label: "This Week", href: "/insights" },
      },
    ],
  },
  {
    slug: "from-simulation-to-price",
    kind: "doctrine",
    title: "From Simulation to Price",
    updatedAt: "2026-08-08",
    tier: "free",
    sports: ["mlb"],
    tags: ["model", "simulation"],
    bottomLine:
      "Distributions become lines; lines become decisions. Simulation is not a pick — it is the machinery that produces a fair you can bet against.",
    keyPoints: [
      "Simulate outcomes → aggregate to team/player markets → compare to board.",
      "Uncertainty belongs in the distribution, not in vibes after the fact.",
      "Only the final price comparison is actionable.",
    ],
    sections: [
      {
        heading: "The pipeline in one pass",
        blocks: [
          "KosEdge models (MLB as the deep example) build from lower-level events upward — matchup, environment, and roster context — into a distribution of scores and props.",
          "That distribution collapses into fair prices: moneyline, spread/run line, total, props. KEI may reprice for information. Edge is still only versus the market you can bet.",
        ],
      },
      {
        heading: "What not to do with sims",
        blocks: [
          [
            "Don't screenshot a single sim path and call it destiny",
            "Don't dump raw model tables into decision-making",
            "Don't skip threshold once the fair looks \"close\"",
          ],
          "The editorial layer (Insights) explains thinking. The boards show the number. Keep them in their lanes.",
        ],
      },
    ],
    whatToDo: [
      {
        text: "See methodology for pipeline framing; use boards for live prices.",
        link: { label: "Methodology", href: "/methodology" },
      },
      {
        text: "For MLB slates, start on Edge Board + KEI — not raw sim dumps.",
        link: { label: "MLB Edge Board", href: "/edge-board/mlb" },
      },
    ],
  },
];

export function getDoctrineArticles(): InsightArticle[] {
  return [...DOCTRINE].sort((a, b) => a.title.localeCompare(b.title));
}

export function getDoctrineBySlug(slug: string): InsightArticle | null {
  return DOCTRINE.find((a) => a.slug === slug) ?? null;
}
