/**
 * CFB conference filter + display affiliation overlay.
 * Power ranks stay on the frozen SoT. A few SoT rows still say Independent
 * for teams that play elsewhere — overlay is display-only, not a second rating.
 */

export const CFB_POWER4 = ["SEC", "Big Ten", "ACC", "Big 12"] as const;

export type CfbConferenceFilter =
  | "all"
  | "p4"
  | "sec"
  | "big-ten"
  | "acc"
  | "big-12"
  | "independent"
  | "aac"
  | "mwc"
  | "sun-belt"
  | "mac"
  | "cusa"
  | "pac-12";

export const CFB_CONFERENCE_FILTERS: {
  key: CfbConferenceFilter;
  label: string;
  href: string;
}[] = [
  { key: "all", label: "All", href: "/pro/cfb/teams" },
  { key: "p4", label: "Power 4", href: "/pro/cfb/teams?conf=p4" },
  { key: "sec", label: "SEC", href: "/pro/cfb/teams?conf=sec" },
  { key: "big-ten", label: "Big Ten", href: "/pro/cfb/teams?conf=big-ten" },
  { key: "acc", label: "ACC", href: "/pro/cfb/teams?conf=acc" },
  { key: "big-12", label: "Big 12", href: "/pro/cfb/teams?conf=big-12" },
  {
    key: "independent",
    label: "Independent",
    href: "/pro/cfb/teams?conf=independent",
  },
  { key: "aac", label: "AAC", href: "/pro/cfb/teams?conf=aac" },
  { key: "mwc", label: "Mountain West", href: "/pro/cfb/teams?conf=mwc" },
  { key: "sun-belt", label: "Sun Belt", href: "/pro/cfb/teams?conf=sun-belt" },
  { key: "mac", label: "MAC", href: "/pro/cfb/teams?conf=mac" },
  { key: "cusa", label: "CUSA", href: "/pro/cfb/teams?conf=cusa" },
  { key: "pac-12", label: "Pac-12", href: "/pro/cfb/teams?conf=pac-12" },
];

/** Display affiliation when SoT conference is a known leftover Independent. */
export const CFB_AFFILIATION_OVERLAY: Record<string, string> = {
  MIZZ: "SEC",
  UNT: "AAC",
  TOL: "MAC",
  UNM: "Mountain West",
  ECU: "AAC",
  ODU: "Sun Belt",
  UAB: "AAC",
  JVST: "CUSA",
  ARST: "Sun Belt",
  NEV: "Mountain West",
  CSU: "Mountain West",
  ARMY: "AAC",
};

const FILTER_TO_CONF: Record<Exclude<CfbConferenceFilter, "all" | "p4">, string> =
  {
    sec: "SEC",
    "big-ten": "Big Ten",
    acc: "ACC",
    "big-12": "Big 12",
    independent: "Independent",
    aac: "AAC",
    mwc: "Mountain West",
    "sun-belt": "Sun Belt",
    mac: "MAC",
    cusa: "CUSA",
    "pac-12": "Pac-12",
  };

export function parseCfbConferenceFilter(raw?: string): CfbConferenceFilter {
  const key = String(raw || "all").trim().toLowerCase();
  if (CFB_CONFERENCE_FILTERS.some((f) => f.key === key)) {
    return key as CfbConferenceFilter;
  }
  return "all";
}

export function displayCfbConference(
  team: string,
  sotConference?: string | null,
): string {
  const overlay = CFB_AFFILIATION_OVERLAY[String(team || "").toUpperCase()];
  return overlay || sotConference || "—";
}

export function teamMatchesConferenceFilter(
  team: string,
  sotConference: string | undefined,
  filter: CfbConferenceFilter,
): boolean {
  if (filter === "all") return true;
  const display = displayCfbConference(team, sotConference);
  if (filter === "p4") {
    return (CFB_POWER4 as readonly string[]).includes(display);
  }
  return display === FILTER_TO_CONF[filter];
}

export function conferencePreviewHref(displayConference: string): string | null {
  const map: Record<string, string> = {
    SEC: "/pro/cfb/conferences/sec",
    "Big Ten": "/pro/cfb/conferences/big-ten",
    ACC: "/pro/cfb/conferences/acc",
    "Big 12": "/pro/cfb/conferences/big-12",
    Independent: "/pro/cfb/conferences/independent",
    AAC: "/pro/cfb/conferences/aac",
    "Mountain West": "/pro/cfb/conferences/mountain-west",
  };
  return map[displayConference] ?? null;
}

const FILTER_PREVIEW_CONF: Partial<Record<CfbConferenceFilter, string>> = {
  sec: "SEC",
  "big-ten": "Big Ten",
  acc: "ACC",
  "big-12": "Big 12",
  independent: "Independent",
  aac: "AAC",
  mwc: "Mountain West",
};

export function conferencePreviewHrefForFilter(
  filter: CfbConferenceFilter,
): string | null {
  const display = FILTER_PREVIEW_CONF[filter];
  return display ? conferencePreviewHref(display) : null;
}

export const CFB_TEAM_DISPLAY_NAMES: Record<string, string> = {
  OSU: "Ohio State",
  ORE: "Oregon",
  MISS: "Ole Miss",
  MIA: "Miami",
  IU: "Indiana",
  TAMU: "Texas A&M",
  ND: "Notre Dame",
  TEX: "Texas",
  UTAH: "Utah",
  OU: "Oklahoma",
  USC: "USC",
  WASH: "Washington",
  AUB: "Auburn",
  SMU: "SMU",
  ARI: "Arizona",
  ALA: "Alabama",
  TTU: "Texas Tech",
  CLEM: "Clemson",
  UGA: "Georgia",
  PSU: "Penn State",
  LOU: "Louisville",
  UVA: "Virginia",
  NCSU: "NC State",
  USF: "South Florida",
  BOISE: "Boise State",
  JMU: "James Madison",
  UTSA: "UTSA",
  UNT: "North Texas",
  TOL: "Toledo",
  HAW: "Hawai'i",
  UNLV: "UNLV",
  MEM: "Memphis",
  TULN: "Tulane",
  CONN: "UConn",
  ARMY: "Army",
  WIS: "Wisconsin",
  BALL: "Ball State",
  STAN: "Stanford",
  FSU: "Florida State",
  LSU: "LSU",
  BAY: "Baylor",
  TXST: "Texas State",
  FIU: "FIU",
  LIB: "Liberty",
  MIZZ: "Missouri",
};

export function cfbTeamDisplayName(code: string): string {
  const key = String(code || "").trim().toUpperCase();
  return CFB_TEAM_DISPLAY_NAMES[key] || key;
}
