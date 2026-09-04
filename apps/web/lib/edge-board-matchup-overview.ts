/**
 * Edge Board matchup overview copy engine.
 * Structure: Bottom line → What matters → What flips.
 * (Former "Watch" heading quarantined — OD-1 / #8 Phase C; no WATCH chrome.)
 * Season gates + neutral-site honesty + desk voice rotation.
 */

import {
  pickDeskVoice,
  type DeskVoiceId,
} from "@/lib/edge-board-desk-voices";
import { MATCHUP_OVERVIEW_FLIPS_HEADING } from "@/lib/edge-board-assemble-quarantine";
import {
  allowsRecentFormLanguage,
  needsEarlySeasonUncertainty,
} from "@/lib/edge-board-season-gates";
import type { EdgeBoardMatchupContext } from "@/lib/edge-board-matchup-context";
import { shortTeam } from "@/lib/edge-board-matchup-context";

export type MatchupOverview = {
  voice: DeskVoiceId;
  bottomLine: string;
  whatMatters: string[];
  watch: string;
  uncertainty?: string;
  /** Formatted card body (no byline). */
  text: string;
};

function fmtSigned(n: number, digits = 1): string {
  const r = Number(n.toFixed(digits));
  if (Object.is(r, -0) || r === 0) return "0";
  return r > 0 ? `+${r.toFixed(digits)}` : r.toFixed(digits);
}

function absEdge(
  kei: number | null,
  mkt: number | null,
): number | null {
  if (kei == null || mkt == null) return null;
  return Math.abs(kei - mkt);
}

function nearMarket(edge: number | null, threshold = 1.0): boolean {
  return edge != null && edge < threshold;
}

function leanSide(ctx: EdgeBoardMatchupContext): "home" | "away" | "push" {
  if (ctx.keiSpreadHome == null || ctx.marketSpreadHome == null) {
    if (ctx.keiSpreadHome == null) return "push";
    // No market — lean to KEI favorite.
    return ctx.keiSpreadHome < 0 ? "home" : ctx.keiSpreadHome > 0 ? "away" : "push";
  }
  const signed = ctx.keiSpreadHome - ctx.marketSpreadHome;
  // Negative signed ⇒ KEI likes home more than market.
  if (Math.abs(signed) < 0.35) return "push";
  return signed < 0 ? "home" : "away";
}

function leanTotal(ctx: EdgeBoardMatchupContext): "over" | "under" | "push" {
  if (ctx.keiTotal == null || ctx.marketTotal == null) return "push";
  const d = ctx.keiTotal - ctx.marketTotal;
  if (Math.abs(d) < 0.75) return "push";
  return d > 0 ? "over" : "under";
}

function siteClause(ctx: EdgeBoardMatchupContext): string | null {
  if (!ctx.isNeutral) return null;
  const city = ctx.siteCity || "a neutral site";
  if (ctx.hfaPoints === 0) {
    return `Neutral site in ${city} — no home-crowd edge for the nominal home side`;
  }
  return `Neutral site in ${city} with partial HFA (${ctx.hfaPoints.toFixed(2)} pts) still in the number`;
}

function powerClause(ctx: EdgeBoardMatchupContext): string | null {
  if (
    ctx.modelPowerAway != null &&
    ctx.modelPowerHome != null
  ) {
    const delta = ctx.modelPowerHome - ctx.modelPowerAway;
    return `${shortTeam(ctx, "home")} model power ${ctx.modelPowerHome.toFixed(1)} vs ${shortTeam(ctx, "away")} ${ctx.modelPowerAway.toFixed(1)} (Δ ${fmtSigned(delta)} E[wins])`;
  }
  if (ctx.keiPowerAway != null && ctx.keiPowerHome != null) {
    const delta = ctx.keiPowerHome - ctx.keiPowerAway;
    return `KEI power gap ${fmtSigned(delta)} pts toward ${delta > 0 ? shortTeam(ctx, "home") : shortTeam(ctx, "away")}`;
  }
  return null;
}

function structuralBullets(ctx: EdgeBoardMatchupContext): string[] {
  const out: string[] = [];
  if (ctx.structuralTagAway) {
    out.push(
      `${shortTeam(ctx, "away")} tag: ${ctx.structuralTagAway} (prior efficiency — not in-season form)`,
    );
  }
  if (ctx.structuralTagHome) {
    out.push(
      `${shortTeam(ctx, "home")} tag: ${ctx.structuralTagHome} (prior efficiency — not in-season form)`,
    );
  }
  return out;
}

function paceBullet(ctx: EdgeBoardMatchupContext): string | null {
  if (ctx.paceAway == null || ctx.paceHome == null) return null;
  const avg = (ctx.paceAway + ctx.paceHome) / 2;
  const label =
    avg >= 1.02 ? "above-average pace" : avg <= 0.96 ? "slower pace" : "mid-pack pace";
  return `Pace proxy ${shortTeam(ctx, "away")} ${ctx.paceAway.toFixed(2)} / ${shortTeam(ctx, "home")} ${ctx.paceHome.toFixed(2)} → ${label}`;
}

function restBullet(ctx: EdgeBoardMatchupContext): string | null {
  if (ctx.seasonGate === "week1") {
    return "Rest: season open — weight travel/neutral and roster construction, not early-week narratives";
  }
  if (ctx.byeAway || ctx.byeHome) {
    const who = [
      ctx.byeAway ? shortTeam(ctx, "away") : null,
      ctx.byeHome ? shortTeam(ctx, "home") : null,
    ]
      .filter(Boolean)
      .join(" / ");
    return `${who} off a bye`;
  }
  if (ctx.restDaysAway != null && ctx.restDaysHome != null) {
    const diff = ctx.restDaysHome - ctx.restDaysAway;
    if (Math.abs(diff) >= 2) {
      return `Rest: ${shortTeam(ctx, "away")} ${Math.round(ctx.restDaysAway)}d vs ${shortTeam(ctx, "home")} ${Math.round(ctx.restDaysHome)}d`;
    }
  }
  return null;
}

function marketSpreadBullet(ctx: EdgeBoardMatchupContext): string | null {
  if (ctx.keiSpreadHome == null) return null;
  const mkt =
    ctx.marketSpreadHome != null
      ? `market ${fmtSigned(ctx.marketSpreadHome)}`
      : "market not posted";
  const edge = absEdge(ctx.keiSpreadHome, ctx.marketSpreadHome);
  if (edge != null && nearMarket(edge, 1.0)) {
    return `Spread: KEI ${fmtSigned(ctx.keiSpreadHome)} ≈ ${mkt} — no forced lean`;
  }
  if (edge != null) {
    const side = leanSide(ctx);
    const who =
      side === "home"
        ? shortTeam(ctx, "home")
        : side === "away"
          ? shortTeam(ctx, "away")
          : "neither side";
    return `Spread: KEI ${fmtSigned(ctx.keiSpreadHome)} vs ${mkt} (${edge.toFixed(1)} pt gap${side === "push" ? "" : ` · ${who}`})`;
  }
  return `Spread: KEI ${fmtSigned(ctx.keiSpreadHome)} (${mkt})`;
}

function marketTotalBullet(ctx: EdgeBoardMatchupContext): string | null {
  if (ctx.keiTotal == null) return null;
  const mkt =
    ctx.marketTotal != null
      ? `market ${ctx.marketTotal.toFixed(1)}`
      : "market not posted";
  const edge = absEdge(ctx.keiTotal, ctx.marketTotal);
  if (edge != null && nearMarket(edge, 1.25)) {
    return `Total: KEI ${ctx.keiTotal.toFixed(1)} ≈ ${mkt}`;
  }
  if (edge != null) {
    const dir = leanTotal(ctx);
    return `Total: KEI ${ctx.keiTotal.toFixed(1)} vs ${mkt}${dir === "push" ? "" : ` · ${dir}`}`;
  }
  return `Total: KEI ${ctx.keiTotal.toFixed(1)} (${mkt})`;
}

function wpBullet(ctx: EdgeBoardMatchupContext): string | null {
  if (ctx.homeWinProb == null && ctx.awayWinProb == null) return null;
  const h = ctx.homeWinProb ?? (ctx.awayWinProb != null ? 1 - ctx.awayWinProb : null);
  const a = ctx.awayWinProb ?? (ctx.homeWinProb != null ? 1 - ctx.homeWinProb : null);
  if (h == null || a == null) return null;
  return `Implied WP ${shortTeam(ctx, "away")} ${Math.round(a * 100)}% / ${shortTeam(ctx, "home")} ${Math.round(h * 100)}%`;
}

function bottomLineForVoice(
  ctx: EdgeBoardMatchupContext,
  voice: DeskVoiceId,
): string {
  const away = shortTeam(ctx, "away");
  const home = shortTeam(ctx, "home");
  const site = siteClause(ctx);
  const spreadEdge = absEdge(ctx.keiSpreadHome, ctx.marketSpreadHome);
  const totalEdge = absEdge(ctx.keiTotal, ctx.marketTotal);
  const side = leanSide(ctx);
  const totalDir = leanTotal(ctx);
  const keiMktClose = nearMarket(spreadEdge, 1.0);

  const open =
    ctx.isNeutral && ctx.siteCity
      ? `${away} vs ${home} in ${ctx.siteCity}`
      : `${away} at ${home}`;

  switch (voice) {
    case "structural": {
      const pow = powerClause(ctx);
      if (pow) {
        return `${open}: ${pow}.${site ? ` ${site}.` : ""}`;
      }
      return `${open}: price this on roster/OL-DL and the posted number${site ? ` — ${site}` : ""}.`;
    }
    case "market": {
      if (ctx.keiSpreadHome != null && ctx.marketSpreadHome != null) {
        if (keiMktClose) {
          return `${open}: KEI ${fmtSigned(ctx.keiSpreadHome)} sits on top of market ${fmtSigned(ctx.marketSpreadHome)} — pass the forced lean.${site ? ` ${site}.` : ""}`;
        }
        const who =
          side === "home" ? home : side === "away" ? away : "the number";
        return `${open}: KEI ${fmtSigned(ctx.keiSpreadHome)} vs market ${fmtSigned(ctx.marketSpreadHome)} (${spreadEdge!.toFixed(1)}) — gap points to ${who}.${site ? ` ${site}.` : ""}`;
      }
      if (ctx.keiSpreadHome != null) {
        return `${open}: KEI home number ${fmtSigned(ctx.keiSpreadHome)}; books still catching up.${site ? ` ${site}.` : ""}`;
      }
      return `${open}: waiting on a clean KEI vs market print.${site ? ` ${site}.` : ""}`;
    }
    case "script_pace": {
      const pace = paceBullet(ctx);
      const tot =
        ctx.keiTotal != null
          ? `KEI total ${ctx.keiTotal.toFixed(1)}${
              ctx.marketTotal != null
                ? ` vs market ${ctx.marketTotal.toFixed(1)}`
                : ""
            }`
          : "total still soft";
      return `${open}: ${pace ? pace.replace(" →", " —") : "pace prior thin"}; ${tot}.${site ? ` ${site}.` : ""}`;
    }
    case "dog": {
      const dog =
        ctx.keiSpreadHome != null
          ? ctx.keiSpreadHome < 0
            ? away
            : home
          : away;
      if (keiMktClose && ctx.marketSpreadHome != null) {
        return `${open}: dog ${dog} is priced fairly vs KEI — no gift on the plus side.${site ? ` ${site}.` : ""}`;
      }
      if (side === "away" || side === "home") {
        const liked = side === "home" ? home : away;
        return `${open}: relative value sits with ${liked} against the board; size only if the price holds.${site ? ` ${site}.` : ""}`;
      }
      return `${open}: dog side needs a number mistake — not a vibes lean.${site ? ` ${site}.` : ""}`;
    }
    case "totals": {
      if (ctx.keiTotal != null && ctx.marketTotal != null) {
        if (nearMarket(totalEdge, 1.25)) {
          return `${open}: totals aligned (KEI ${ctx.keiTotal.toFixed(1)} ≈ ${ctx.marketTotal.toFixed(1)}).${site ? ` ${site}.` : ""}`;
        }
        return `${open}: KEI total ${ctx.keiTotal.toFixed(1)} vs market ${ctx.marketTotal.toFixed(1)} — ${totalDir === "push" ? "thin" : totalDir}.${site ? ` ${site}.` : ""}`;
      }
      if (ctx.keiTotal != null) {
        return `${open}: KEI total ${ctx.keiTotal.toFixed(1)}; market total not posted yet.${site ? ` ${site}.` : ""}`;
      }
      return `${open}: total board incomplete — hold the over/under lean.${site ? ` ${site}.` : ""}`;
    }
  }
}

function whatMattersForVoice(
  ctx: EdgeBoardMatchupContext,
  voice: DeskVoiceId,
): string[] {
  const bullets: string[] = [];
  const site = siteClause(ctx);
  if (site) bullets.push(site);

  const spread = marketSpreadBullet(ctx);
  const total = marketTotalBullet(ctx);
  const wp = wpBullet(ctx);
  const pace = paceBullet(ctx);
  const rest = restBullet(ctx);
  const struct = structuralBullets(ctx);
  const pow = powerClause(ctx);

  const pushUnique = (s: string | null | undefined) => {
    if (!s) return;
    if (!bullets.includes(s)) bullets.push(s);
  };

  switch (voice) {
    case "structural":
      pushUnique(pow);
      for (const s of struct) pushUnique(s);
      pushUnique(rest);
      pushUnique(spread);
      break;
    case "market":
      pushUnique(spread);
      pushUnique(total);
      pushUnique(wp);
      pushUnique(site);
      break;
    case "script_pace":
      pushUnique(pace);
      pushUnique(total);
      pushUnique(struct[0] ?? null);
      pushUnique(spread);
      break;
    case "dog":
      pushUnique(spread);
      pushUnique(wp);
      pushUnique(pow);
      pushUnique(rest);
      break;
    case "totals":
      pushUnique(total);
      pushUnique(pace);
      pushUnique(struct[0] ?? null);
      pushUnique(spread);
      break;
  }

  // Early season: never inject recent-form bullets.
  if (allowsRecentFormLanguage(ctx.seasonGate)) {
    // Reserved: only when caller supplies labeled form evidence later.
  }

  // Cap 2–4.
  const trimmed = bullets.filter(Boolean).slice(0, 4);
  if (trimmed.length < 2) {
    pushUnique(
      ctx.seasonGate === "week1"
        ? "Week 1 / first game: roster, OL/DL, QB situation, and the market number — not trailing form"
        : "Lean on posted KEI vs market; omit missing inputs",
    );
    return bullets.filter(Boolean).slice(0, 4);
  }
  return trimmed;
}

function watchForVoice(
  ctx: EdgeBoardMatchupContext,
  voice: DeskVoiceId,
): string {
  const side = leanSide(ctx);
  const totalDir = leanTotal(ctx);
  const spreadEdge = absEdge(ctx.keiSpreadHome, ctx.marketSpreadHome);

  if (ctx.isNeutral && ctx.hfaPoints === 0) {
    return "If the board still prices a full home-crowd HFA, the number is lying about the site.";
  }

  switch (voice) {
    case "structural":
      return ctx.seasonGate === "week1"
        ? "One OL/DL or QB availability flip moves this more than any early-season streak story."
        : "If the structural tags disagree with the spread, trust the price gap — not the story.";
    case "market":
      if (nearMarket(spreadEdge, 1.0)) {
        return "Watch for a book to hang a soft alternate — that is the only market edge left.";
      }
      return side === "push"
        ? "A half-point cross on a key number flips the playability faster than any new narrative."
        : `If ${side === "home" ? shortTeam(ctx, "home") : shortTeam(ctx, "away")}’s price disappears, the edge left with it.`;
    case "script_pace":
      return totalDir === "under"
        ? "If early downs stall, the under script was the real bet — not the side."
        : "If both offenses hit explosive pace, the total thesis beats the side thesis.";
    case "dog":
      return "Live only if the plus-number is still up; a steamed favorite kills the dog thesis.";
    case "totals":
      return totalDir === "push"
        ? "No total lean until KEI and market separate by a full point."
        : `A weather or pace confirmation is the only green light for the ${totalDir}.`;
  }
}

function uncertaintyClause(ctx: EdgeBoardMatchupContext): string | undefined {
  if (!needsEarlySeasonUncertainty(ctx.seasonGate)) return undefined;
  if (ctx.seasonGate === "week1") {
    return "Early-season uncertainty: no trailing sample yet — this is structure + price only.";
  }
  if (ctx.seasonGate === "early") {
    return "Early-season sample is thin — weight structure and the number over short trailing samples.";
  }
  return "Inputs incomplete — omit anything we cannot see.";
}

export function formatMatchupOverview(parts: {
  bottomLine: string;
  whatMatters: string[];
  watch: string;
  uncertainty?: string;
}): string {
  const lines = [
    "Bottom line",
    parts.bottomLine,
    "",
    "What matters",
    ...parts.whatMatters.map((b) => `• ${b}`),
    "",
    MATCHUP_OVERVIEW_FLIPS_HEADING,
    parts.watch,
  ];
  if (parts.uncertainty) {
    lines.push("", parts.uncertainty);
  }
  return lines.join("\n");
}

export function buildMatchupOverview(
  ctx: EdgeBoardMatchupContext,
): MatchupOverview {
  const voice = pickDeskVoice(ctx.gameId);
  const bottomLine = bottomLineForVoice(ctx, voice);
  const whatMatters = whatMattersForVoice(ctx, voice);
  const watch = watchForVoice(ctx, voice);
  const uncertainty = uncertaintyClause(ctx);
  return {
    voice,
    bottomLine,
    whatMatters,
    watch,
    uncertainty,
    text: formatMatchupOverview({
      bottomLine,
      whatMatters,
      watch,
      uncertainty,
    }),
  };
}

/**
 * Convenience for Edge Board cards — builds overview text from context.
 * Non-NFL / thin context still gets the structured template (no boilerplate pros/cons).
 */
export function generateStructuredGameOverview(
  ctx: EdgeBoardMatchupContext,
): string {
  return buildMatchupOverview(ctx).text;
}
