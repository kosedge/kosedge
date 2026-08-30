import type { SportKey } from "@/lib/sports";

export type WriterId =
  | "casey-voss"
  | "reese-quinn"
  | "morgan-hale"
  | "taylor-brooks"
  | "avery-cole";

export type WriterProfile = {
  id: WriterId;
  name: string;
  shortName: string;
};

export type TeamResearchDataStatus = "live" | "pending";

export type TeamResearchSectionKey =
  | "preview"
  | "roster"
  | "depth"
  | "coaching"
  | "stats"
  | "ats"
  | "injuries"
  | "rest_travel"
  | "park_factors"
  | "splits"
  | "form"
  | "schedule"
  | "market_links";

export type TeamResearchSectionConfig = {
  key: TeamResearchSectionKey;
  title: string;
  /** Short sport-aware description shown above the body / empty state */
  description: string;
  status: TeamResearchDataStatus;
  emptyCopy: string;
};

export type TeamDirectoryEntry = {
  /** URL slug — lowercase abbr for pro leagues, name slug for college */
  slug: string;
  /** Short code shown in UI (BUF, NYY, LAL) */
  code: string;
  name: string;
  /** Conference / league grouping (AFC, AL, Western, SEC, …) */
  conference: string;
  /** Division when the sport uses one (North, Central, Atlantic, …) */
  division?: string;
  city?: string;
};

export type TeamResearchSportConfig = {
  sportKey: SportKey;
  directoryLabel: string;
  summary: string;
  /** Depth chart vs rotation / lineup label */
  depthLabel: string;
  /** HC + coordinators vs manager / bench coach, etc. */
  coachingLabel: string;
  statsLabels: string[];
  sections: TeamResearchSectionConfig[];
  marketLinks: Array<{ href: string; label: string }>;
};

export type TeamResearchIdentity = {
  sportKey: SportKey;
  team: TeamDirectoryEntry;
  recordLabel: string;
  conferenceLine: string;
  nextGameLabel: string | null;
  writer: WriterProfile;
  writerAssignmentNote: string;
};
