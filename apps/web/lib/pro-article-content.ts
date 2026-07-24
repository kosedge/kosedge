import type { LegacyEdgeBoardRow } from "@/components/EdgeBoard";
import { hasArticleData } from "@/lib/pro-sport-ia";

type SportContent = {
  mode: "full" | "placeholder";
  marketContext: string;
  modelEdge: string;
  matchupDrivers: string[];
  riskFactors: string[];
  confidence: string;
};

type SportProfile = {
  edgeExecutionNote: string;
  movementFallback: string;
  drivers: string[];
  risks: string[];
};

function parseSpread(label: string): number | null {
  const n = Number.parseFloat(String(label).replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function parseTotal(label: string): number | null {
  const n = Number.parseFloat(String(label).replace(/[^\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function movementSummary(row: LegacyEdgeBoardRow): string {
  const openSpread = parseSpread(row.openLine.top.label);
  const bestSpread = parseSpread(row.bestLine.top.label);
  const openTotal = parseTotal(row.openOU.top.label);
  const bestTotal = parseTotal(row.bestOU.top.label);

  const spreadShift =
    openSpread != null && bestSpread != null
      ? Math.abs(bestSpread - openSpread)
      : null;
  const totalShift =
    openTotal != null && bestTotal != null
      ? Math.abs(bestTotal - openTotal)
      : null;

  const spreadText =
    spreadShift != null
      ? `Spread moved ${spreadShift.toFixed(1)} points from open to current best.`
      : "Spread change is limited due to incomplete open data.";
  const totalText =
    totalShift != null
      ? `Total moved ${totalShift.toFixed(1)} points versus opener.`
      : "Total movement is still stabilizing.";

  return `${spreadText} ${totalText}`;
}

function confidenceFromEdges(row: LegacyEdgeBoardRow): string {
  const strongest = Math.max(row.edgeLineNum ?? 0, row.edgeOUNum ?? 0);
  if (strongest >= 2.5) {
    return "High-confidence setup: model-market separation is wide enough to survive normal late-week volatility.";
  }
  if (strongest >= 1.0) {
    return "Moderate confidence: there is measurable model value, but execution timing and injury updates remain important.";
  }
  return "Low confidence: keep this matchup on watchlist status unless numbers drift back to model fair value.";
}

function teamHash(value: string): number {
  let out = 0;
  for (let i = 0; i < value.length; i++) {
    out = (out * 31 + value.charCodeAt(i)) >>> 0;
  }
  return out;
}

function pick<T>(arr: T[], seed: number, count: number): T[] {
  return Array.from({ length: count }, (_, index) => {
    const item = arr[(seed + index * 11) % arr.length];
    return item as T;
  });
}

const SPORT_PROFILES: Record<string, SportProfile> = {
  nfl: {
    edgeExecutionNote:
      "Execution focuses on key spread bands (3, 6, 7) and late injury confirmation windows.",
    movementFallback:
      "Market is still shaping around key numbers, so confirmation from injury and weather feeds matters.",
    drivers: [
      "Early-down success rate and second-and-medium frequency.",
      "Pressure rate versus pass-protection grade under true dropback conditions.",
      "Explosive pass allowance (20+ yard plays) versus vertical route tendency.",
      "Red-zone touchdown efficiency and play-calling split inside the 10.",
      "Neutral-situation pace and no-huddle usage when trailing by one score.",
      "Run-fit integrity versus gap-scheme carry rate on early downs.",
      "Third-down pass rate over expectation against coverage shell tendencies.",
    ],
    risks: [
      "Final injury designations can materially change pass-protection and secondary matchups.",
      "Weather and wind shifts can compress expected explosive pass volume.",
      "Late steam around key numbers can erase execution value quickly.",
    ],
  },
  cfb: {
    edgeExecutionNote:
      "Execution leans on pace mismatch, havoc differential, and market reaction to confirmed starters.",
    movementFallback:
      "College market limits and lineup uncertainty can delay true price discovery until late in the week.",
    drivers: [
      "Explosiveness allowed versus opponent isoPPP and chunk-play profile.",
      "Havoc rate (sacks, TFLs, turnovers) versus offensive line disruption tolerance.",
      "Early-down EPA and schedule-adjusted success rate by field zone.",
      "Red-zone touchdown conversion versus opponent red-zone stop rate.",
      "Tempo divergence and possession count sensitivity in game script extremes.",
      "Special teams field-position edge and hidden-yardage swing potential.",
      "Passing downs efficiency versus pressure package frequency.",
    ],
    risks: [
      "Depth-chart volatility and late quarterback confirmation can reprice games quickly.",
      "Travel, altitude, and weather factors can distort historical team baselines.",
      "Market limits can create sharper late moves than early numbers imply.",
    ],
  },
  nba: {
    edgeExecutionNote:
      "Execution emphasizes confirmed rotations, pace environment, and fatigue-adjusted shot quality.",
    movementFallback:
      "Numbers are still settling around availability signals and expected rotation depth.",
    drivers: [
      "Half-court shot quality versus transition dependence in projected pace states.",
      "Pick-and-roll efficiency and rim pressure against drop/switch coverage tendencies.",
      "Defensive rebounding control and second-chance suppression rate.",
      "Corner-three volume allowed versus opponent catch-and-shoot creation.",
      "Bench on/off stability when primary creators sit.",
      "Foul drawing frequency versus opponent free-throw suppression profile.",
      "Late-game execution in one-possession clutch environments.",
    ],
    risks: [
      "Rest management and late scratches can materially shift usage concentration.",
      "Back-to-back fatigue effects can alter pace and defensive closeout quality.",
      "Derivative markets may lag mainline repricing after injury confirmations.",
    ],
  },
  wnba: {
    edgeExecutionNote:
      "Execution prioritizes usage concentration, turnover control, and travel-related pace shifts.",
    movementFallback:
      "Market depth can be uneven, so confirmation through multiple books is important before sizing.",
    drivers: [
      "Assist-to-turnover profile versus opponent ball-pressure intensity.",
      "Rim frequency and paint efficiency against interior foul discipline.",
      "Pace control and transition denial in possession-sensitive matchups.",
      "Offensive rebounding pressure versus box-out conversion reliability.",
      "Primary-creator usage concentration and secondary shot-creation support.",
      "Perimeter shot profile stability under heavy minutes loads.",
      "Late-clock execution against switching or trap-heavy coverages.",
    ],
    risks: [
      "Rotation compression and condensed travel can affect shooting legs late.",
      "Lower-liquidity windows can create abrupt price steps across books.",
      "Key-guard availability changes can re-rate turnover and pace assumptions.",
    ],
  },
  ncaam: {
    edgeExecutionNote:
      "Execution centers on tempo expectation, turnover profile, and matchup-specific rebounding leverage.",
    movementFallback:
      "Price discovery is still stabilizing as lineup notes and market limits mature through the day.",
    drivers: [
      "Tempo divergence and possession ceiling relative to each team baseline.",
      "Turnover creation versus press-break and ball-security profile.",
      "Half-court shot quality and rim-attempt share by lineup mix.",
      "Offensive rebounding pressure versus opponent defensive glass control.",
      "Three-point attempt rate allowed versus catch-and-shoot quality.",
      "Foul profile and free-throw rate differential in projected whistle environments.",
      "Late-game execution and timeout efficiency in close scripts.",
    ],
    risks: [
      "Rotation uncertainty and foul exposure can change expected possession value.",
      "Early tip-off scheduling or travel spots can suppress offensive efficiency.",
      "Smaller market windows can amplify late corrections around key totals.",
    ],
  },
  mlb: {
    edgeExecutionNote:
      "Execution focuses on starter quality, bullpen leverage sequencing, and park/weather run environment.",
    movementFallback:
      "Price action remains sensitive to probable starter updates and bullpen availability.",
    drivers: [
      "Starting pitcher arsenal fit versus projected lineup handedness splits.",
      "Bullpen leverage depth and bridge-inning stability after the starter exits.",
      "Ground-ball/fly-ball profile against park dimensions and weather carry.",
      "Team swing-decision quality against expected zone and chase profile.",
      "Base-running pressure and catcher control in close-run scripts.",
      "Defensive run prevention at key positions in high-contact environments.",
      "Times-through-order penalty risk against opponent lineup depth.",
    ],
    risks: [
      "Late lineup scratches and catcher/rest decisions can shift run environment quickly.",
      "Bullpen usage from prior games can alter true late-inning projection quality.",
      "Wind direction changes can materially impact total-value assumptions.",
    ],
  },
  nhl: {
    edgeExecutionNote:
      "Execution emphasizes confirmed goaltenders, five-on-five shot quality, and special-teams discipline.",
    movementFallback:
      "Market clarity improves after goalie confirmation and late line-combination updates.",
    drivers: [
      "Expected-goals profile at five-on-five versus opponent chance suppression.",
      "Goaltender form and rebound-control trend over recent starts.",
      "Power-play chance creation versus penalty-kill denial structure.",
      "Neutral-zone entry efficiency and controlled-zone-time sustainability.",
      "Faceoff deployment in offensive-zone starts for top scoring lines.",
      "Blue-line puck movement quality versus forecheck pressure rates.",
      "Backcheck recovery speed in odd-man rush prevention.",
    ],
    risks: [
      "Goaltender confirmation timing can reprice both side and total quickly.",
      "Special-teams variance can dominate outcomes in low-event games.",
      "Schedule congestion can reduce forecheck intensity and late-game pace.",
    ],
  },
};

function getSportProfile(sport: string): SportProfile {
  return (
    SPORT_PROFILES[sport] ?? {
      edgeExecutionNote:
        "Execution should remain disciplined against market depth and confirmation quality.",
      movementFallback:
        "Market movement remains in discovery; prioritize confirmation before increasing exposure.",
      drivers: [
        "Pace and possession profile relative to league baseline.",
        "Efficiency split in set-play versus transition/live-ball states.",
        "Turnover creation and conversion into high-leverage scoring chances.",
        "Late-game closing reliability in one-possession scripts.",
      ],
      risks: [
        "Line availability and hold variation across books can impact execution value.",
        "Late roster or rotation news can shift projections materially.",
        "Consensus may compress before expected liquidity windows.",
      ],
    }
  );
}

export function buildProArticleContent({
  sport,
  row,
}: {
  sport: string;
  row: LegacyEdgeBoardRow;
}): SportContent {
  const away = row.teamA.name;
  const home = row.teamB.name;
  const lineEdge = row.edgeLineNum;
  const totalEdge = row.edgeOUNum;
  const sportProfile = getSportProfile(sport);
  const isDataReady = hasArticleData(row);

  if (!isDataReady) {
    return {
      mode: "placeholder",
      marketContext: `${away} at ${home} is in premium placeholder mode while line and total feeds finish validation for this slate.`,
      modelEdge:
        "Model edge and execution guidance are temporarily withheld until pricing and availability data meet launch confidence thresholds.",
      matchupDrivers: [
        "Core market feeds are still syncing for this matchup.",
        "Starter or lineup confirmation is pending from primary data sources.",
        "Article intelligence unlocks automatically once validation completes.",
      ],
      riskFactors: [
        "Incomplete market context can misrepresent true edge quality.",
        "Late feed corrections may materially shift spread or total baseline.",
        "Execution windows should remain watchlist-only until status upgrades.",
      ],
      confidence:
        "Data pending: this matchup remains premium watchlist-only until feed quality checks pass.",
    };
  }

  const edgeSummary =
    lineEdge != null || totalEdge != null
      ? `Current model edge reads ${
          lineEdge != null
            ? `${lineEdge.toFixed(1)} points on spread`
            : "no clear spread edge"
        } and ${
          totalEdge != null
            ? `${totalEdge.toFixed(1)} points on total`
            : "no clear total edge"
        }.`
      : "Model edge values are not fully available yet; execution should remain conservative.";

  return {
    mode: "full",
    marketContext: `${away} at ${home} is trading with ${row.bestLine.top.label} as best spread and ${row.bestOU.top.label} as best total. ${movementSummary(row)} ${sportProfile.movementFallback}`,
    modelEdge: `${edgeSummary} ${sportProfile.edgeExecutionNote}`,
    matchupDrivers: pick(sportProfile.drivers, teamHash(`${away}-${home}`), 3),
    riskFactors: sportProfile.risks,
    confidence: confidenceFromEdges(row),
  };
}
