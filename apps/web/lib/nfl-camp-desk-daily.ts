/**
 * Camp Desk daily product — KosEdge notes, not ESPN card titles.
 * Pure helpers (no fs) so tests can lock sort / max-age / copy rules.
 */

export const CAMP_DESK_MAX_AGE_MS = 72 * 60 * 60 * 1000;

export type CampDeskSource = {
  label: string;
  href: string;
};

export type CampLeagueWrap = {
  title: string;
  bottom_line: string;
  storylines: string[];
  what_to_watch: string;
  sources: CampDeskSource[];
};

export type CampTeamNote = {
  team_id: string;
  title: string;
  bottom_line: string;
  key_points: string[];
  what_to_watch: string;
  is_material_depth: boolean;
  sot_flag?: string;
  sources: CampDeskSource[];
};

export type CampPreviewDelta = {
  team_id: string;
  fields: string[];
  reason: string;
  status: "flagged" | "touched" | "skipped";
};

export type CampDeskDayFile = {
  desk_date: string;
  pinned?: boolean;
  source_type: "kosedge-desk";
  league_wrap: CampLeagueWrap;
  team_notes: CampTeamNote[];
  preview_delta?: CampPreviewDelta[];
};

export type CampDeskCard = {
  id: string;
  kind: "league_wrap" | "team_note";
  desk_date: string;
  pinned: boolean;
  team_ids: string[];
  source_type: "kosedge-desk";
  is_material_depth: boolean;
  sot_flag: string | null;
  title: string;
  bottom_line: string;
  key_points: string[];
  what_to_watch: string;
  sources: CampDeskSource[];
  href?: string;
};

export function parseDeskDateMs(deskDate: string): number {
  const ts = Date.parse(`${deskDate}T12:00:00-04:00`);
  return Number.isFinite(ts) ? ts : 0;
}

export function isWithinCampDeskWindow(
  deskDate: string,
  now: Date,
  pinned = false,
): boolean {
  if (pinned) return true;
  const start = parseDeskDateMs(deskDate);
  if (!start) return false;
  return now.getTime() - start <= CAMP_DESK_MAX_AGE_MS;
}

export function formatCampDeskDayLabel(deskDate: string): string {
  const ts = parseDeskDateMs(deskDate);
  if (!ts) return deskDate;
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
    timeZone: "America/New_York",
  }).format(new Date(ts));
}

export function formatCampDeskShortDate(deskDate: string): string {
  const ts = parseDeskDateMs(deskDate);
  if (!ts) return deskDate;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "America/New_York",
  }).format(new Date(ts));
}

export function cardsFromDayFile(
  file: CampDeskDayFile,
  pinnedOverride?: boolean,
): CampDeskCard[] {
  const pinned = pinnedOverride ?? Boolean(file.pinned);
  const wrap: CampDeskCard = {
    id: `wrap-${file.desk_date}`,
    kind: "league_wrap",
    desk_date: file.desk_date,
    pinned,
    team_ids: file.team_notes.map((note) => note.team_id),
    source_type: "kosedge-desk",
    is_material_depth: file.team_notes.some((note) => note.is_material_depth),
    sot_flag: null,
    title: file.league_wrap.title,
    bottom_line: file.league_wrap.bottom_line,
    key_points: file.league_wrap.storylines,
    what_to_watch: file.league_wrap.what_to_watch,
    sources: file.league_wrap.sources,
  };
  const notes: CampDeskCard[] = file.team_notes.map((note) => ({
    id: `note-${file.desk_date}-${note.team_id}`,
    kind: "team_note",
    desk_date: file.desk_date,
    pinned,
    team_ids: [note.team_id],
    source_type: "kosedge-desk",
    is_material_depth: note.is_material_depth,
    sot_flag: note.sot_flag ?? null,
    title: note.title,
    bottom_line: note.bottom_line,
    key_points: note.key_points,
    what_to_watch: note.what_to_watch,
    sources: note.sources,
    href: `/pro/nfl/previews/${note.team_id}`,
  }));
  return [wrap, ...notes];
}

export function selectCampDeskCards(
  cards: CampDeskCard[],
  opts: {
    now: Date;
    team?: string | null;
    inCamp?: boolean;
  },
): CampDeskCard[] {
  const team = opts.team?.trim().toUpperCase() || null;
  const inCamp = opts.inCamp ?? true;
  return cards
    .filter((card) => {
      if (team && card.kind === "team_note" && !card.team_ids.includes(team)) {
        return false;
      }
      if (team && card.kind === "league_wrap") return true;
      if (!inCamp) return true;
      return isWithinCampDeskWindow(card.desk_date, opts.now, card.pinned);
    })
    .sort((a, b) => {
      const dateDelta = parseDeskDateMs(b.desk_date) - parseDeskDateMs(a.desk_date);
      if (dateDelta !== 0) return dateDelta;
      if (a.kind !== b.kind) return a.kind === "league_wrap" ? -1 : 1;
      return a.id.localeCompare(b.id);
    });
}

export function collectSotFlags(cards: CampDeskCard[]): CampDeskCard[] {
  return cards.filter((card) => card.is_material_depth && card.kind === "team_note");
}

export function collectPreviewDeltas(files: CampDeskDayFile[]): CampPreviewDelta[] {
  return files.flatMap((file) => file.preview_delta ?? []);
}
