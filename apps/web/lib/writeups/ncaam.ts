// apps/web/lib/writeups/ncaam.ts
import { format } from "date-fns";

export type NcaamGameContext = {
  eventId: string;
  gameDate: string; // ISO YYYY-MM-DD
  homeTeam: string;
  awayTeam: string;
  neutral: boolean;
  venue?: string | null;
  conferenceHome?: string | null;
  conferenceAway?: string | null;
  isTournament?: boolean;
  modelSpread: number; // home perspective (negative = home favored)
  marketSpreadClose: number | null;
  edgeClose: number | null;
  modelTotal?: number | null;
  marketTotalClose?: number | null;
  totalEdge?: number | null;
  restDaysHome?: number | null;
  restDaysAway?: number | null;
  travelMilesAway?: number | null;
  keyPlayerOutHome?: boolean | null;
  keyPlayerOutAway?: boolean | null;
};

function fmtTeam(name: string) {
  return name;
}

function fmtSpread(value: number | null) {
  if (value == null) return "N/A";
  const rounded = Math.round(value * 10) / 10;
  if (rounded === 0) return "PK";
  return rounded > 0 ? `+${rounded}` : `${rounded}`;
}

function fmtEdge(value: number | null) {
  if (value == null) return "no clear edge";
  const rounded = Math.round(value * 10) / 10;
  if (Math.abs(rounded) < 0.5) return "a very small edge";
  const dir = rounded > 0 ? "toward the home side" : "toward the road side";
  return `${Math.abs(rounded).toFixed(1)} points ${dir}`;
}

function describeVenue(ctx: NcaamGameContext) {
  const dateLabel = format(new Date(ctx.gameDate), "EEE, MMM d");
  if (ctx.neutral) {
    if (ctx.isTournament) {
      return `${dateLabel} on a neutral floor, likely in conference or postseason tournament play.`;
    }
    return `${dateLabel} on a neutral court, with neither team holding a traditional home edge.`;
  }
  return `${dateLabel} at ${fmtTeam(ctx.homeTeam)}, with the usual home-court advantage in play.`;
}

function describeContext(ctx: NcaamGameContext) {
  const parts: string[] = [];

  if (ctx.conferenceHome && ctx.conferenceAway) {
    if (ctx.conferenceHome === ctx.conferenceAway) {
      parts.push(`${fmtTeam(ctx.awayTeam)} visits a conference rival in ${ctx.conferenceHome}.`);
    } else {
      parts.push(
        `${fmtTeam(ctx.awayTeam)} from ${ctx.conferenceAway} matches up with ${fmtTeam(
          ctx.homeTeam,
        )} out of ${ctx.conferenceHome}.`,
      );
    }
  } else {
    parts.push(`${fmtTeam(ctx.awayTeam)} faces ${fmtTeam(ctx.homeTeam)} in NCAAM action.`);
  }

  if (ctx.isTournament) {
    parts.push("This sets up as a tournament game where motivation and rotations can be a bit different.");
  }

  return parts.join(" ");
}

function describeRestAndTravel(ctx: NcaamGameContext) {
  const { restDaysHome, restDaysAway, travelMilesAway } = ctx;
  const lines: string[] = [];

  if (restDaysHome != null && restDaysAway != null) {
    const diff = restDaysHome - restDaysAway;
    if (diff >= 2) {
      lines.push(`${fmtTeam(ctx.homeTeam)} has a notable rest advantage (${restDaysHome} days vs ${restDaysAway}).`);
    } else if (diff >= 1) {
      lines.push(`${fmtTeam(ctx.homeTeam)} is slightly fresher (${restDaysHome} days rest vs ${restDaysAway}).`);
    } else if (diff <= -2) {
      lines.push(`${fmtTeam(ctx.awayTeam)} comes in much fresher on rest (${restDaysAway} days vs ${restDaysHome}).`);
    }
  }

  if (travelMilesAway != null && travelMilesAway >= 500) {
    lines.push(
      `${fmtTeam(ctx.awayTeam)} also draws a meaningful travel spot (~${Math.round(
        travelMilesAway,
      )} miles), which can show up late.`,
    );
  }

  return lines.join(" ");
}

function describeInjuries(ctx: NcaamGameContext) {
  const lines: string[] = [];
  if (ctx.keyPlayerOutHome) {
    lines.push(`${fmtTeam(ctx.homeTeam)} is flagged with at least one key player unavailable.`);
  }
  if (ctx.keyPlayerOutAway) {
    lines.push(`${fmtTeam(ctx.awayTeam)} is also dealing with a key absence.`);
  }
  return lines.join(" ");
}

export function buildNcaamWriteup(ctx: NcaamGameContext): string {
  const parts: string[] = [];

  // Headline context
  parts.push(describeVenue(ctx));
  parts.push(describeContext(ctx));

  // Model vs market on side
  const marketSpread = ctx.marketSpreadClose;
  const modelSpread = ctx.modelSpread;
  const edge = ctx.edgeClose;

  if (marketSpread != null && edge != null) {
    const modelLabel =
      modelSpread < 0
        ? `${fmtTeam(ctx.homeTeam)} -${Math.abs(Math.round(modelSpread * 10) / 10)}`
        : `${fmtTeam(ctx.awayTeam)} +${Math.round(modelSpread * 10) / 10}`;
    const marketLabel = `market around ${fmtSpread(marketSpread)}`;

    parts.push(
      `Our college basketball model makes the fair line ${modelLabel}, with the ${marketLabel} ` +
        `implying an edge of ${fmtEdge(edge)} against the spread.`,
    );
  } else {
    parts.push("Our NCAAM model is aligned with this market, with no clear edge showing on the spread.");
  }

  // Totals, when available
  if (ctx.modelTotal != null && ctx.marketTotalClose != null && ctx.totalEdge != null) {
    const totalEdgeAbs = Math.abs(Math.round(ctx.totalEdge * 10) / 10);
    const lean =
      ctx.totalEdge > 0
        ? "slightly toward the over"
        : ctx.totalEdge < 0
        ? "slightly toward the under"
        : "without a strong lean";
    parts.push(
      `On the total, our projection sits at ${Math.round(ctx.modelTotal * 10) / 10} versus a market number of ` +
        `${Math.round(ctx.marketTotalClose * 10) / 10}, an edge of about ${totalEdgeAbs.toFixed(
          1,
        )} points ${lean}.`,
    );
  }

  // Rest / travel
  const restTravel = describeRestAndTravel(ctx);
  if (restTravel) {
    parts.push(restTravel);
  }

  // Injuries
  const inj = describeInjuries(ctx);
  if (inj) {
    parts.push(inj);
  }

  return parts.join(" ");
}

