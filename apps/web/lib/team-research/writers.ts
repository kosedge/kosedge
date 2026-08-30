import type { SportKey } from "@/lib/sports";
import type { TeamDirectoryEntry, WriterId, WriterProfile } from "./types";

export const WRITERS: Record<WriterId, WriterProfile> = {
  "casey-voss": {
    id: "casey-voss",
    name: "Casey Voss",
    shortName: "Casey",
  },
  "reese-quinn": {
    id: "reese-quinn",
    name: "Reese Quinn",
    shortName: "Reese",
  },
  "morgan-hale": {
    id: "morgan-hale",
    name: "Morgan Hale",
    shortName: "Morgan",
  },
  "taylor-brooks": {
    id: "taylor-brooks",
    name: "Taylor Brooks",
    shortName: "Taylor",
  },
  "avery-cole": {
    id: "avery-cole",
    name: "Avery Cole",
    shortName: "Avery",
  },
};

/**
 * Coverage matrix from `.cursor/rules/ai-writer-team.mdc`.
 * Primary owner wins on home base; “also covers” fills the rest.
 */
const NFL_DIVISION_OWNER: Record<string, WriterId> = {
  "NFC|North": "casey-voss",
  "AFC|North": "reese-quinn",
  "AFC|West": "reese-quinn",
  "NFC|West": "morgan-hale",
  "AFC|East": "taylor-brooks",
  "AFC|South": "taylor-brooks",
  "NFC|South": "avery-cole",
  "NFC|East": "avery-cole",
};

const MLB_OWNER: Record<string, WriterId> = {
  // Taylor primary on Central; Casey also covers — primary wins
  "AL|Central": "taylor-brooks",
  "NL|Central": "taylor-brooks",
  "AL|West": "reese-quinn",
  "NL|West": "morgan-hale",
  "AL|East": "taylor-brooks",
  "NL|East": "avery-cole",
};

const NBA_OWNER: Record<string, WriterId> = {
  Northwest: "casey-voss", // also Reese primary — Casey listed on also-covers
  Pacific: "morgan-hale",
  Southwest: "taylor-brooks",
  Atlantic: "avery-cole",
  Southeast: "avery-cole",
  Central: "casey-voss",
};

/** Reese is primary on NBA Northwest; override Casey also-covers. */
const NBA_PRIMARY_OVERRIDE: Record<string, WriterId> = {
  Northwest: "reese-quinn",
};

const NHL_OWNER: Record<string, WriterId> = {
  Central: "morgan-hale", // Casey also covers; Morgan is primary
  Pacific: "reese-quinn",
  Metropolitan: "morgan-hale",
  Atlantic: "taylor-brooks",
};

const WNBA_OWNER: Record<string, WriterId> = {
  Western: "avery-cole", // Casey also covers; Avery is primary
  Eastern: "reese-quinn",
};

/**
 * College sports are outside the locked pro matrix.
 * Assign by conference region so every team still shows a preview owner.
 * Marked provisional in the UI assignment note.
 */
const COLLEGE_CONFERENCE_OWNER: Record<string, WriterId> = {
  // Football
  SEC: "avery-cole",
  ACC: "avery-cole",
  "Big Ten": "casey-voss",
  "Big 12": "taylor-brooks",
  "Pac-12": "morgan-hale",
  AAC: "reese-quinn",
  "Mountain West": "morgan-hale",
  "Sun Belt": "avery-cole",
  MAC: "casey-voss",
  CUSA: "taylor-brooks",
  Independent: "reese-quinn",
  // Basketball extras
  "Big East": "reese-quinn",
  "Atlantic 10": "taylor-brooks",
  WCC: "morgan-hale",
  MVC: "casey-voss",
  American: "reese-quinn",
  "Conference USA": "taylor-brooks",
  "West Coast": "morgan-hale",
  Ivy: "taylor-brooks",
  "Atlantic Sun": "avery-cole",
  Southland: "taylor-brooks",
};

function key(conference: string, division?: string): string {
  return division ? `${conference}|${division}` : conference;
}

export type WriterAssignment = {
  writer: WriterProfile;
  /** Human-readable source of the assignment */
  note: string;
  provisional: boolean;
};

export function assignTeamPreviewWriter(
  sportKey: SportKey,
  team: TeamDirectoryEntry,
): WriterAssignment {
  const conf = team.conference;
  const div = team.division;

  if (sportKey === "nfl") {
    const id =
      NFL_DIVISION_OWNER[key(conf, div)] ??
      NFL_DIVISION_OWNER[key(conf, "North")] ??
      "casey-voss";
    return {
      writer: WRITERS[id],
      note: `Coverage matrix · ${conf} ${div ?? ""}`.trim(),
      provisional: false,
    };
  }

  if (sportKey === "mlb") {
    const id = MLB_OWNER[key(conf, div)] ?? "taylor-brooks";
    return {
      writer: WRITERS[id],
      note: `Coverage matrix · ${conf} ${div ?? "Central"}`.trim(),
      provisional: false,
    };
  }

  if (sportKey === "nba") {
    const divKey = div ?? conf;
    const id =
      NBA_PRIMARY_OVERRIDE[divKey] ?? NBA_OWNER[divKey] ?? "reese-quinn";
    return {
      writer: WRITERS[id],
      note: `Coverage matrix · NBA ${divKey}`,
      provisional: false,
    };
  }

  if (sportKey === "nhl") {
    const divKey = div ?? conf;
    const id = NHL_OWNER[divKey] ?? "morgan-hale";
    // Morgan primary on Central; Casey also covers — primary wins
    return {
      writer: WRITERS[id],
      note: `Coverage matrix · NHL ${divKey}`,
      provisional: false,
    };
  }

  if (sportKey === "wnba") {
    const confKey = conf.includes("West") ? "Western" : "Eastern";
    const id = WNBA_OWNER[confKey] ?? "avery-cole";
    return {
      writer: WRITERS[id],
      note: `Coverage matrix · WNBA ${confKey}`,
      provisional: false,
    };
  }

  // CFB / NCAAM — provisional regional desk
  const collegeId =
    COLLEGE_CONFERENCE_OWNER[conf] ??
    COLLEGE_CONFERENCE_OWNER[conf.replace(" Conference", "")] ??
    hashWriter(team.slug);
  return {
    writer: WRITERS[collegeId],
    note: `Provisional college desk · ${conf}`,
    provisional: true,
  };
}

function hashWriter(slug: string): WriterId {
  const ids = Object.keys(WRITERS) as WriterId[];
  let h = 0;
  for (let i = 0; i < slug.length; i++) h = (h * 31 + slug.charCodeAt(i)) >>> 0;
  return ids[h % ids.length]!;
}
