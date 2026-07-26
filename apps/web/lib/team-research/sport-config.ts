import type { SportKey } from "@/lib/sports";
import type {
  TeamResearchSectionConfig,
  TeamResearchSportConfig,
} from "./types";

function section(
  partial: TeamResearchSectionConfig,
): TeamResearchSectionConfig {
  return partial;
}

function marketLinks(
  sportKey: SportKey,
): TeamResearchSportConfig["marketLinks"] {
  const base = `/pro/${sportKey}`;
  if (sportKey === "nfl") {
    return [
      { href: "/edge-board/nfl", label: "Edge board" },
      { href: "/pro/nfl/fair-lines", label: "KEI lines" },
      { href: "/pro/nfl/edges", label: "Edges desk" },
      { href: "/odds/nfl", label: "Compare odds" },
      { href: "/pro/nfl/teams", label: "Team intel index" },
    ];
  }
  if (sportKey === "mlb") {
    return [
      { href: "/edge-board/mlb", label: "Edge board" },
      { href: "/pro/mlb/fair-lines", label: "Fair lines" },
      { href: "/pro/mlb/edges", label: "Edges desk" },
      { href: "/odds/mlb", label: "Compare odds" },
      { href: `${base}/overview`, label: "MLB hub" },
    ];
  }
  return [
    { href: `/edge-board/${sportKey}`, label: "Edge board" },
    { href: `${base}/fair-lines`, label: "Fair lines" },
    { href: `/odds/${sportKey}`, label: "Compare odds" },
    { href: `/pro/power-ratings/${sportKey}`, label: "Power ratings" },
    { href: `${base}/overview`, label: "Sport hub" },
  ];
}

const PREVIEW = (sportName: string) =>
  section({
    key: "preview",
    title: "Season preview",
    description: `AI writer season preview slot for ${sportName} handicapping context.`,
    status: "pending",
    emptyCopy:
      "Season preview coming soon. Writer ownership is assigned; article text is not invented until research is delivered.",
  });

function footballSections(sportName: string): TeamResearchSectionConfig[] {
  return [
    PREVIEW(sportName),
    section({
      key: "roster",
      title: "Roster",
      description: "Active roster hierarchy for role and availability context.",
      status: "pending",
      emptyCopy: "Roster feed pending for this sport.",
    }),
    section({
      key: "depth",
      title: "Depth chart",
      description: "Position-group depth for injury and matchup leverage.",
      status: "pending",
      emptyCopy: "Depth chart data pending.",
    }),
    section({
      key: "coaching",
      title: "Coaching staff",
      description: "Head coach, offensive coordinator, defensive coordinator.",
      status: "pending",
      emptyCopy: "Coaching profile data pending.",
    }),
    section({
      key: "stats",
      title: "Team stats",
      description: "Offense, defense, and special teams efficiency baselines.",
      status: "pending",
      emptyCopy: "Team stats pending model/intel wiring.",
    }),
    section({
      key: "ats",
      title: "ATS & totals",
      description: "Against-the-spread and over/under records when available.",
      status: "pending",
      emptyCopy: "ATS / OU records — data pending.",
    }),
    section({
      key: "injuries",
      title: "Injury list",
      description: "Availability that changes pricing assumptions.",
      status: "pending",
      emptyCopy: "Injury report pending sport health feed.",
    }),
    section({
      key: "rest_travel",
      title: "Rest & travel",
      description: "Days rest, travel distance, and short-week flags.",
      status: "pending",
      emptyCopy: "Rest / travel context — data pending.",
    }),
    section({
      key: "form",
      title: "Recent form",
      description: "Last-N results and efficiency trend direction.",
      status: "pending",
      emptyCopy: "Recent form cards — data pending.",
    }),
    section({
      key: "schedule",
      title: "Schedule strength",
      description: "Remaining slate difficulty and key number spots.",
      status: "pending",
      emptyCopy: "Schedule strength — data pending.",
    }),
    section({
      key: "market_links",
      title: "Market desks",
      description: "Jump into live boards and fair-line tools.",
      status: "live",
      emptyCopy: "",
    }),
  ];
}

function baseballSections(): TeamResearchSectionConfig[] {
  return [
    PREVIEW("MLB"),
    section({
      key: "roster",
      title: "Roster",
      description: "Active roster with pitcher / position splits.",
      status: "pending",
      emptyCopy: "Roster feed pending.",
    }),
    section({
      key: "depth",
      title: "Lineup & rotation",
      description: "Expected batting order and starting rotation depth.",
      status: "pending",
      emptyCopy: "Lineup / rotation confirmation pending daily feed.",
    }),
    section({
      key: "coaching",
      title: "Manager & bench",
      description: "Manager, bench coach, and pitching coach profile.",
      status: "pending",
      emptyCopy: "Coaching profile data pending.",
    }),
    section({
      key: "stats",
      title: "Team stats",
      description:
        "Run differential, wRC+, FIP environment, and bullpen marks.",
      status: "pending",
      emptyCopy: "Club stats pending intel tables.",
    }),
    section({
      key: "park_factors",
      title: "Park factors",
      description: "Home run-environment reference used in totals framing.",
      status: "live",
      emptyCopy: "Park factor unavailable for this club.",
    }),
    section({
      key: "ats",
      title: "ATS & totals",
      description: "Run-line and over/under records when available.",
      status: "pending",
      emptyCopy: "ATS / OU records — data pending.",
    }),
    section({
      key: "injuries",
      title: "IL / availability",
      description: "Injured list and day-to-day availability.",
      status: "pending",
      emptyCopy: "Availability feed pending.",
    }),
    section({
      key: "splits",
      title: "Home / away splits",
      description: "Park-aware home and road offensive/defensive splits.",
      status: "pending",
      emptyCopy: "Home/away splits — data pending.",
    }),
    section({
      key: "form",
      title: "Recent form",
      description: "Last 10 and starter/bullpen form windows.",
      status: "pending",
      emptyCopy: "Recent form — data pending.",
    }),
    section({
      key: "market_links",
      title: "Market desks",
      description: "Fair lines, edges, and public boards.",
      status: "live",
      emptyCopy: "",
    }),
  ];
}

function basketballSections(sportName: string): TeamResearchSectionConfig[] {
  return [
    PREVIEW(sportName),
    section({
      key: "roster",
      title: "Roster",
      description: "Active roster with usage and minutes context.",
      status: "pending",
      emptyCopy: "Roster feed pending.",
    }),
    section({
      key: "depth",
      title: "Rotation",
      description: "Projected rotation and minutes distribution.",
      status: "pending",
      emptyCopy: "Rotation depth pending availability feed.",
    }),
    section({
      key: "coaching",
      title: "Coaching staff",
      description: "Head coach and primary assistants.",
      status: "pending",
      emptyCopy: "Coaching profile data pending.",
    }),
    section({
      key: "stats",
      title: "Team stats",
      description: "Pace, offensive/defensive rating, and net rating.",
      status: "pending",
      emptyCopy: "Efficiency stats pending model board wiring.",
    }),
    section({
      key: "ats",
      title: "ATS & totals",
      description: "Spread and total records when available.",
      status: "pending",
      emptyCopy: "ATS / OU records — data pending.",
    }),
    section({
      key: "injuries",
      title: "Injury report",
      description: "Availability shocks that reprice sides and totals.",
      status: "pending",
      emptyCopy: "Injury report pending.",
    }),
    section({
      key: "rest_travel",
      title: "Rest & travel",
      description: "Back-to-backs, three-in-fours, and travel load.",
      status: "pending",
      emptyCopy: "Rest / travel flags — data pending.",
    }),
    section({
      key: "splits",
      title: "Home / away splits",
      description: "Location splits for side and total framing.",
      status: "pending",
      emptyCopy: "Home/away splits — data pending.",
    }),
    section({
      key: "form",
      title: "Recent form",
      description: "Last-10 net rating and ATS direction.",
      status: "pending",
      emptyCopy: "Recent form — data pending.",
    }),
    section({
      key: "market_links",
      title: "Market desks",
      description: "Boards and fair-line tools for this league.",
      status: "live",
      emptyCopy: "",
    }),
  ];
}

function hockeySections(): TeamResearchSectionConfig[] {
  return [
    PREVIEW("NHL"),
    section({
      key: "roster",
      title: "Roster",
      description: "Skaters and goalie tandem for matchup prep.",
      status: "pending",
      emptyCopy: "Roster feed pending.",
    }),
    section({
      key: "depth",
      title: "Lines & pairs",
      description: "Forward lines, defense pairs, and goalie confirmation.",
      status: "pending",
      emptyCopy: "Line combinations pending daily desk feed.",
    }),
    section({
      key: "coaching",
      title: "Coaching staff",
      description: "Head coach and associate / assistant structure.",
      status: "pending",
      emptyCopy: "Coaching profile data pending.",
    }),
    section({
      key: "stats",
      title: "Team stats",
      description:
        "Five-on-five xG, special teams, and goalie save environment.",
      status: "pending",
      emptyCopy: "Team rates pending feed wiring.",
    }),
    section({
      key: "ats",
      title: "Puck line & totals",
      description: "Puck-line and over/under records when available.",
      status: "pending",
      emptyCopy: "ATS / OU records — data pending.",
    }),
    section({
      key: "injuries",
      title: "Injury list",
      description: "Skater and goalie availability.",
      status: "pending",
      emptyCopy: "Injury list pending.",
    }),
    section({
      key: "rest_travel",
      title: "Rest & travel",
      description: "Back-to-backs and road trip load.",
      status: "pending",
      emptyCopy: "Rest / travel — data pending.",
    }),
    section({
      key: "form",
      title: "Recent form",
      description: "Last-10 results and five-on-five trend.",
      status: "pending",
      emptyCopy: "Recent form — data pending.",
    }),
    section({
      key: "market_links",
      title: "Market desks",
      description: "Fair lines, edges, and goalie desk entry points.",
      status: "live",
      emptyCopy: "",
    }),
  ];
}

/** NFL uses dedicated intel routes; research sections overlay overview. */
function nflResearchSections(): TeamResearchSectionConfig[] {
  return [
    PREVIEW("NFL"),
    section({
      key: "roster",
      title: "Roster",
      description: "Live from NFL intel when season/week filters resolve.",
      status: "live",
      emptyCopy: "Roster hierarchy still populating for this period.",
    }),
    section({
      key: "depth",
      title: "Depth chart",
      description: "Live depth-chart records from NFL intel.",
      status: "live",
      emptyCopy: "Depth chart records pending for this filter.",
    }),
    section({
      key: "coaching",
      title: "Coaching staff",
      description: "Head coach, OC, and DC profiles for scheme context.",
      status: "pending",
      emptyCopy:
        "Coaching profile data pending — scheme notes ship with writer desk.",
    }),
    section({
      key: "stats",
      title: "Team stats",
      description:
        "Live EPA, pass rate, and situational splits from NFL intel.",
      status: "live",
      emptyCopy: "Stat profile unavailable for this filter.",
    }),
    section({
      key: "ats",
      title: "ATS & totals",
      description: "Against-the-spread and over/under records.",
      status: "pending",
      emptyCopy: "ATS / OU records — data pending.",
    }),
    section({
      key: "injuries",
      title: "Injury list",
      description: "Live injury report from NFL intel.",
      status: "live",
      emptyCopy: "No injury rows for this team and week.",
    }),
    section({
      key: "rest_travel",
      title: "Rest & travel",
      description: "Bye weeks, short weeks, and travel flags.",
      status: "pending",
      emptyCopy: "Rest / travel context — data pending.",
    }),
    section({
      key: "form",
      title: "Recent form & trends",
      description: "Trend snippets derived from live weekly stats.",
      status: "live",
      emptyCopy: "Trend signals unavailable until stats load.",
    }),
    section({
      key: "market_links",
      title: "Market desks",
      description: "KEI lines, edges, and public boards.",
      status: "live",
      emptyCopy: "",
    }),
  ];
}

const CONFIGS: Record<SportKey, TeamResearchSportConfig> = {
  nfl: {
    sportKey: "nfl",
    directoryLabel: "NFL Team Research",
    summary:
      "Handicapping research pages with live intel where wired, plus writer-owned season preview slots.",
    depthLabel: "Depth chart",
    coachingLabel: "HC / OC / DC",
    statsLabels: ["Pass rate", "Off EPA/play", "Def EPA allowed", "RZ TD rate"],
    sections: nflResearchSections(),
    marketLinks: marketLinks("nfl"),
  },
  mlb: {
    sportKey: "mlb",
    directoryLabel: "MLB Team Research",
    summary:
      "Club research shells for starters, bullpens, park factors, and writer-owned season previews.",
    depthLabel: "Lineup & rotation",
    coachingLabel: "Manager & bench",
    statsLabels: ["Run differential", "wRC+", "FIP", "Bullpen innings"],
    sections: baseballSections(),
    marketLinks: marketLinks("mlb"),
  },
  nba: {
    sportKey: "nba",
    directoryLabel: "NBA Team Research",
    summary:
      "Team research shells for pace, net rating, rotation health, and writer-owned season previews.",
    depthLabel: "Rotation",
    coachingLabel: "Head coach",
    statsLabels: ["Pace", "Off rating", "Def rating", "Net rating"],
    sections: basketballSections("NBA"),
    marketLinks: marketLinks("nba"),
  },
  nhl: {
    sportKey: "nhl",
    directoryLabel: "NHL Team Research",
    summary:
      "Team research shells for goalie confirmation, five-on-five rates, and writer-owned season previews.",
    depthLabel: "Lines & pairs",
    coachingLabel: "Head coach",
    statsLabels: ["xGF%", "Special teams", "GSAx", "PDO"],
    sections: hockeySections(),
    marketLinks: marketLinks("nhl"),
  },
  wnba: {
    sportKey: "wnba",
    directoryLabel: "WNBA Team Research",
    summary:
      "Team research shells for usage concentration, travel load, and writer-owned season previews.",
    depthLabel: "Rotation",
    coachingLabel: "Head coach",
    statsLabels: ["Pace", "Off rating", "Def rating", "Usage leaders"],
    sections: basketballSections("WNBA"),
    marketLinks: marketLinks("wnba"),
  },
  cfb: {
    sportKey: "cfb",
    directoryLabel: "CFB Team Research",
    summary:
      "FBS research shells for tempo, havoc, depth, and provisional writer preview ownership.",
    depthLabel: "Depth chart",
    coachingLabel: "HC / OC / DC",
    statsLabels: ["Tempo", "Havoc", "Explosiveness", "Success rate"],
    sections: footballSections("CFB"),
    marketLinks: marketLinks("cfb"),
  },
  ncaam: {
    sportKey: "ncaam",
    directoryLabel: "CBB Team Research",
    summary:
      "College basketball research shells for tempo, efficiency, and provisional writer preview ownership.",
    depthLabel: "Rotation",
    coachingLabel: "Head coach",
    statsLabels: ["Tempo", "Off efficiency", "Def efficiency", "Variance"],
    sections: basketballSections("CBB"),
    marketLinks: marketLinks("ncaam"),
  },
};

export function getTeamResearchSportConfig(
  sportKey: string,
): TeamResearchSportConfig | null {
  if (sportKey in CONFIGS) return CONFIGS[sportKey as SportKey];
  return null;
}

export function listTeamResearchSportKeys(): SportKey[] {
  return Object.keys(CONFIGS) as SportKey[];
}
