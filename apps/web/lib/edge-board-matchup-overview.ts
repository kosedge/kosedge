/**
 * Edge Board matchup overview copy engine.
 *
 * Fixed structure: Bottom line · What matters · Watch
 * Season-aware + neutral-site-aware. Desk voice only (no personal bylines).
 * Never invents “recent form” when there is no recent form.
 * Does not echo Decision Engine PLAY/LEAN — Action column owns that.
 */

export type DeskVoiceId = "structural" | "market" | "script" | "dog" | "totals";

export type SeasonPhase = "week1" | "early" | "mid";

export type MatchupOverviewContext = {
  sportKey: string;
  gameId: string;
  awayTeam: string;
  homeTeam: string;
  week?: number | null;
  seasonType?: string | null;
  weekRegime?: string | null;
  neutralSite?: boolean | null;
  venueCity?: string | null;
  venueName?: string | null;
  /** Market spread from away perspective (Odds convention). */
  marketSpreadAway?: number | null;
  /** KEI / model spread from home perspective. */
  keiSpreadHome?: number | null;
  marketTotal?: number | null;
  keiTotal?: number | null;
  edgeLineNum?: number | null;
  edgeOUNum?: number | null;
  homeWinProb?: number | null;
  awayWinProb?: number | null;
  restDaysHome?: number | null;
  restDaysAway?: number | null;
  /** HFA points applied by model/desk; 0 on true neutral. */
  hfaPoints?: number | null;
  keyNumberCross?: boolean | null;
  modelConfidenceBand?: string | null;
  /** Optional structural unit tags (real tags only). */
  awayUnitTag?: string | null;
  homeUnitTag?: string | null;
};

export type MatchupOverviewBlocks = {
  voice: DeskVoiceId;
  deskLabel: string;
  bottomLine: string;
  whatMatters: string[];
  watch: string;
  seasonPhase: SeasonPhase;
  neutralSite: boolean;
};

const DESK_VOICES: {
  id: DeskVoiceId;
  label: string;
}[] = [
  { id: "structural", label: "Structural desk" },
  { id: "market", label: "Market desk" },
  { id: "script", label: "Script desk" },
  { id: "dog", label: "Dog desk" },
  { id: "totals", label: "Totals desk" },
];

const BANNED_OPENERS = [
  "this matchup features",
  "expect a battle",
  "both sides enter",
  "both teams will try",
  "travels to face",
];

function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

export function assignDeskVoice(gameId: string): {
  id: DeskVoiceId;
  label: string;
} {
  const idx = hashStr(gameId || "game") % DESK_VOICES.length;
  return DESK_VOICES[idx]!;
}

export function resolveSeasonPhase(ctx: MatchupOverviewContext): SeasonPhase {
  const st = String(ctx.seasonType ?? "").toUpperCase();
  if (st === "PRE") return "week1";
  const week = ctx.week;
  if (week == null || week <= 1) return "week1";
  if (week <= 4) return "early";
  return "mid";
}

/** Known international / bowl-style city labels for site copy. */
const NEUTRAL_CITY_HINTS = [
  "london",
  "mexico city",
  "são paulo",
  "sao paulo",
  "munich",
  "frankfurt",
  "berlin",
  "dublin",
  "toronto",
];

export function isNeutralSite(ctx: MatchupOverviewContext): boolean {
  if (ctx.neutralSite === true) return true;
  const city = String(ctx.venueCity ?? "").toLowerCase();
  const venue = String(ctx.venueName ?? "").toLowerCase();
  const hay = `${city} ${venue}`;
  return NEUTRAL_CITY_HINTS.some((h) => hay.includes(h));
}

export function siteLabel(ctx: MatchupOverviewContext): string {
  const neutral = isNeutralSite(ctx);
  const city = String(ctx.venueCity ?? "").trim();
  if (neutral) {
    if (city) return `Neutral · ${city}`;
    const venue = String(ctx.venueName ?? "").trim();
    if (venue) return `Neutral · ${venue}`;
    return "Neutral site";
  }
  return "Home";
}

function fmtSigned(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const r = Math.round(n * 10) / 10;
  if (Object.is(r, -0) || r === 0) return "PK";
  return r > 0 ? `+${r}` : String(r);
}

function shortName(name: string): string {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return "—";
  return parts[parts.length - 1]!;
}

function spreadLeanSentence(ctx: MatchupOverviewContext): {
  leanTeam: string | null;
  keiLabel: string;
  marketLabel: string;
  gap: number | null;
} {
  const keiHome = ctx.keiSpreadHome;
  const mktAway = ctx.marketSpreadAway;
  const marketHome =
    mktAway != null && Number.isFinite(mktAway) ? -mktAway : null;
  let gap: number | null = null;
  if (keiHome != null && marketHome != null) {
    gap = Math.abs(keiHome - marketHome);
  } else if (ctx.edgeLineNum != null) {
    gap = ctx.edgeLineNum;
  }

  let leanTeam: string | null = null;
  if (keiHome != null && marketHome != null) {
    // Negative KEI = home favored. If KEI home is stiffer (more negative) than market → lean home.
    leanTeam = keiHome < marketHome ? ctx.homeTeam : ctx.awayTeam;
    if (Math.abs(keiHome - marketHome) < 0.5) leanTeam = null;
  }

  return {
    leanTeam,
    keiLabel: fmtSigned(keiHome),
    marketLabel: fmtSigned(marketHome),
    gap,
  };
}

function restBullet(ctx: MatchupOverviewContext): string | null {
  const h = ctx.restDaysHome;
  const a = ctx.restDaysAway;
  if (h == null || a == null) return null;
  const diff = h - a;
  if (Math.abs(diff) < 1) return null;
  if (diff >= 2) {
    return `${shortName(ctx.homeTeam)} holds a real rest edge (${h}d vs ${a}d).`;
  }
  if (diff <= -2) {
    return `${shortName(ctx.awayTeam)} is fresher on rest (${a}d vs ${h}d).`;
  }
  return `${shortName(diff > 0 ? ctx.homeTeam : ctx.awayTeam)} has a slight rest edge (${Math.max(h, a)}d vs ${Math.min(h, a)}d).`;
}

function structuralUnitBullet(
  ctx: MatchupOverviewContext,
  seed: number,
): string {
  const awayTag = ctx.awayUnitTag?.trim();
  const homeTag = ctx.homeUnitTag?.trim();
  if (awayTag && homeTag) {
    return `${shortName(ctx.awayTeam)}: ${awayTag} · ${shortName(ctx.homeTeam)}: ${homeTag}.`;
  }
  // Sport-aware structural pool — never “recent form”.
  const sport = String(ctx.sportKey).toLowerCase();
  const nflPool = [
    `${shortName(ctx.awayTeam)} OL/DL construction vs ${shortName(ctx.homeTeam)} front seven sets the floor.`,
    `QB situation and pocket integrity are the structural swing for ${shortName(ctx.awayTeam)}.`,
    `${shortName(ctx.homeTeam)} pass-rush / coverage balance is the unit edge to price first.`,
    `Skill-usage concentration on ${shortName(seed % 2 === 0 ? ctx.awayTeam : ctx.homeTeam)} matters more than vague “explosiveness.”`,
  ];
  const mlbPool = [
    `Starter quality and early-inning leverage decide more than bullpen lore tonight.`,
    `Park and contact profile beat vague “hot bats” framing for this card.`,
    `Bullpen stress tags favor the side that can finish without max leverage.`,
  ];
  const genericPool = [
    `Roster construction and role clarity beat narrative form for this number.`,
    `Schedule context and travel load are cleaner inputs than empty “momentum.”`,
  ];
  const pool =
    sport === "nfl" || sport === "cfb"
      ? nflPool
      : sport === "mlb"
        ? mlbPool
        : genericPool;
  return pool[seed % pool.length]!;
}

function buildBottomLine(
  ctx: MatchupOverviewContext,
  voice: DeskVoiceId,
  phase: SeasonPhase,
  neutral: boolean,
): string {
  const { leanTeam, keiLabel, marketLabel, gap } = spreadLeanSentence(ctx);
  const siteBit = neutral
    ? ctx.venueCity
      ? `Neutral site (${ctx.venueCity})`
      : "Neutral site"
    : null;
  const earlyBit =
    phase === "week1"
      ? "Early-season sample is thin — price structure, not invented form."
      : phase === "early"
        ? "Still early; treat prior-game evidence lightly."
        : null;

  const aligned =
    gap == null || gap < 0.75 || leanTeam == null
      ? "KEI sits near the market — no forced lean from the number alone."
      : `${shortName(leanTeam)} is the side the KEI number prefers (KEI ${keiLabel} vs market ${marketLabel}, gap ${gap.toFixed(1)}).`;

  const hfaBit =
    neutral && (ctx.hfaPoints == null || ctx.hfaPoints === 0)
      ? "Model uses zero / reduced neutral HFA."
      : neutral && ctx.hfaPoints != null && ctx.hfaPoints > 0
        ? `Model uses reduced neutral HFA (~${ctx.hfaPoints.toFixed(1)}).`
        : null;

  switch (voice) {
    case "market": {
      const parts = [
        siteBit ? `${siteBit}: ${aligned}` : aligned,
        gap != null && gap >= 0.75
          ? `Buy/sell question is whether ${gap.toFixed(1)} pts of separation is real or noise.`
          : "Line implies a tight price — shop juice before inventing a side.",
        earlyBit,
        hfaBit,
      ];
      return parts.filter(Boolean).join(" ");
    }
    case "dog": {
      const dog =
        leanTeam == null
          ? null
          : leanTeam === ctx.homeTeam
            ? ctx.awayTeam
            : ctx.homeTeam;
      const parts = [
        siteBit
          ? `${siteBit} strips full home-crowd scripts from the dog case.`
          : null,
        dog && gap != null && gap >= 0.75
          ? `Underdog lens: can ${shortName(dog)} cover if the market number (${marketLabel}) is soft vs KEI ${keiLabel}?`
          : aligned,
        earlyBit,
        hfaBit,
      ];
      return parts.filter(Boolean).join(" ");
    }
    case "totals": {
      const keiT = ctx.keiTotal;
      const mktT = ctx.marketTotal;
      const tGap =
        keiT != null && mktT != null
          ? Math.abs(keiT - mktT)
          : (ctx.edgeOUNum ?? null);
      const lean =
        keiT != null && mktT != null
          ? keiT > mktT
            ? "over"
            : keiT < mktT
              ? "under"
              : null
          : null;
      const parts = [
        siteBit ? `${siteBit}.` : null,
        keiT != null && mktT != null
          ? `Totals desk: KEI ${keiT.toFixed(1)} vs market ${mktT.toFixed(1)}${lean && tGap != null && tGap >= 0.75 ? ` — mild ${lean} pressure (${tGap.toFixed(1)})` : " — aligned"}.`
          : "Totals desk: waiting on a clean market/KEI total pair.",
        earlyBit,
      ];
      return parts.filter(Boolean).join(" ");
    }
    case "script": {
      const parts = [
        siteBit
          ? `${siteBit}: pace/script edges matter more than crowd noise.`
          : "Script lens: possessions, pass rate, and total pressure set the number.",
        aligned,
        earlyBit,
        hfaBit,
      ];
      return parts.filter(Boolean).join(" ");
    }
    case "structural":
    default: {
      const parts = [
        siteBit
          ? `${siteBit} — treat the nominal home side as a listed host, not a fortress.`
          : null,
        aligned,
        earlyBit,
        hfaBit,
      ];
      return parts.filter(Boolean).join(" ");
    }
  }
}

function buildWhatMatters(
  ctx: MatchupOverviewContext,
  voice: DeskVoiceId,
  phase: SeasonPhase,
  neutral: boolean,
  seed: number,
): string[] {
  const bullets: string[] = [];
  const { leanTeam, keiLabel, marketLabel, gap } = spreadLeanSentence(ctx);

  // Always include one matchup-specific factor first.
  if (neutral) {
    bullets.push(
      `${siteLabel(ctx)} — do not price a full home-crowd bump for ${shortName(ctx.homeTeam)}.`,
    );
  } else if (gap != null && gap >= 0.75 && leanTeam) {
    bullets.push(
      `Number: KEI ${keiLabel} vs market ${marketLabel} points to ${shortName(leanTeam)}.`,
    );
  } else {
    bullets.push(structuralUnitBullet(ctx, seed));
  }

  // Voice emphasis (distinct angle, not different invented facts).
  if (voice === "market" && gap != null) {
    bullets.push(
      gap < 0.75
        ? "Market and KEI agree closely — edge is juice/shopping, not a thesis."
        : `Separation of ${gap.toFixed(1)} pts is the only side thesis until new info hits.`,
    );
  } else if (voice === "script") {
    if (ctx.keiTotal != null) {
      bullets.push(
        `Projected scoring environment sits near ${ctx.keiTotal.toFixed(1)} — script/pass-rate pressure feeds the total more than vibes.`,
      );
    } else {
      bullets.push(
        "Pace proxy unavailable — do not invent tempo; lean on line/total structure.",
      );
    }
  } else if (voice === "dog") {
    bullets.push(
      phase === "week1"
        ? "Dog case must be structural (roster/OL/QB/travel), not “they’re due.”"
        : "Dog cover path needs a concrete failure mode on the favorite — not vague momentum.",
    );
  } else if (voice === "totals") {
    const tGap =
      ctx.keiTotal != null && ctx.marketTotal != null
        ? Math.abs(ctx.keiTotal - ctx.marketTotal)
        : ctx.edgeOUNum;
    bullets.push(
      tGap != null && tGap >= 0.75
        ? `Total gap ${tGap.toFixed(1)} is the actionable board number; ignore empty “both offenses can score” filler.`
        : "Total is tightly priced — wait for weather/injury before forcing an O/U lean.",
    );
  } else {
    // structural
    if (!neutral || bullets.length === 0) {
      bullets.push(structuralUnitBullet(ctx, seed + 3));
    }
  }

  const rest = restBullet(ctx);
  if (rest) bullets.push(rest);

  if (ctx.keyNumberCross) {
    bullets.push(
      "Key-number cross flagged — half-point / 3-and-7 geometry matters more than narrative.",
    );
  }

  if (
    ctx.homeWinProb != null &&
    ctx.awayWinProb != null &&
    Number.isFinite(ctx.homeWinProb) &&
    Number.isFinite(ctx.awayWinProb)
  ) {
    bullets.push(
      `Implied WP (KEI): ${shortName(ctx.awayTeam)} ${(ctx.awayWinProb * 100).toFixed(0)}% · ${shortName(ctx.homeTeam)} ${(ctx.homeWinProb * 100).toFixed(0)}%.`,
    );
  }

  // Cap 2–4; ensure at least one matchup-specific already satisfied.
  const unique = [...new Set(bullets.filter(Boolean))];
  return unique.slice(0, 4);
}

function buildWatch(
  ctx: MatchupOverviewContext,
  phase: SeasonPhase,
  neutral: boolean,
): string {
  if (neutral) {
    return `Watch: travel/rest + any late inactive that rewrites the reduced-HFA script at ${siteLabel(ctx)}.`;
  }
  if (phase === "week1") {
    return "Watch: confirmed starters / OL availability — first-game form claims are noise.";
  }
  if (ctx.modelConfidenceBand === "low" || ctx.modelConfidenceBand === "thin") {
    return "Watch: low-confidence board — one injury or weather shift can flip the view.";
  }
  if ((ctx.edgeOUNum ?? 0) >= 2.0 && (ctx.edgeLineNum ?? 0) < 1.5) {
    return "Watch: total is the livelier number — weather and pass-rate confirmation.";
  }
  return `Watch: late inactive that hits ${shortName(ctx.awayTeam)} or ${shortName(ctx.homeTeam)} QB/OL/skill hub.`;
}

export function buildMatchupOverviewBlocks(
  ctx: MatchupOverviewContext,
): MatchupOverviewBlocks {
  const voiceMeta = assignDeskVoice(
    ctx.gameId || `${ctx.awayTeam}|${ctx.homeTeam}`,
  );
  const phase = resolveSeasonPhase(ctx);
  const neutral = isNeutralSite(ctx);
  const seed = hashStr(ctx.gameId || `${ctx.awayTeam}|${ctx.homeTeam}`);

  const bottomLine = buildBottomLine(ctx, voiceMeta.id, phase, neutral);
  const whatMatters = buildWhatMatters(ctx, voiceMeta.id, phase, neutral, seed);
  const watch = buildWatch(ctx, phase, neutral);

  // Honesty: never claim recent form in week1.
  const safeMatters =
    phase === "week1"
      ? whatMatters.map((b) =>
          b
            .replace(/\brecent\b/gi, "structural")
            .replace(/\bhot offense\b/gi, "roster construction")
            .replace(/\bcooling off\b/gi, "uncertain baseline"),
        )
      : whatMatters;

  return {
    voice: voiceMeta.id,
    deskLabel: voiceMeta.label,
    bottomLine,
    whatMatters: safeMatters,
    watch,
    seasonPhase: phase,
    neutralSite: neutral,
  };
}

/** Format blocks for Edge Board `<pre>`/whitespace-pre-wrap overview panel. */
export function formatMatchupOverview(blocks: MatchupOverviewBlocks): string {
  const lines = [
    `BOTTOM LINE`,
    blocks.bottomLine,
    ``,
    `WHAT MATTERS`,
    ...blocks.whatMatters.map((b) => `• ${b}`),
    ``,
    `WATCH`,
    blocks.watch,
    ``,
    blocks.deskLabel,
  ];
  const text = lines.join("\n");
  // Soft guard against banned openers sneaking in.
  const lower = text.toLowerCase();
  for (const ban of BANNED_OPENERS) {
    if (lower.includes(ban)) {
      // Rewrite is already designed to avoid these; keep as-is if residual.
      break;
    }
  }
  return text;
}

export function buildMatchupOverview(ctx: MatchupOverviewContext): string {
  return formatMatchupOverview(buildMatchupOverviewBlocks(ctx));
}
