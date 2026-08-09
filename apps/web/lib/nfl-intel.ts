import { env } from "@/lib/config/env";
import { formatIntelNumber } from "@/lib/intel-numeric";
import { resolveConferenceDivision } from "@/lib/nfl-team-intel";

export type NflIntelResponseRow = Record<string, unknown>;

export type NflIntelResponse = {
  season: number | null;
  week: number | null;
  team: string | null;
  count: number;
  rows: NflIntelResponseRow[];
  selection?: {
    requested?: {
      season?: number | null;
      week?: number | null;
      team?: string | null;
    };
    resolved?: {
      season?: number | null;
      week?: number | null;
      team?: string | null;
    };
    used_default?: {
      season?: boolean;
      week?: boolean;
      any?: boolean;
    };
    latest_available?: {
      season?: number | null;
      week?: number | null;
      row_count?: number;
      team_count?: number;
    };
    requested_availability?: {
      season?: number | null;
      week?: number | null;
      row_count?: number;
      team_count?: number;
      has_data?: boolean | null;
    } | null;
    fallback_applied?: boolean;
  };
  error?: string;
};

function toText(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number")
    return Number.isFinite(value) ? String(value) : "—";
  const text = String(value).trim();
  return text.length > 0 ? text : "—";
}

export function formatIntelValue(value: unknown): string {
  if (typeof value === "number") {
    return formatIntelNumber(value, true);
  }
  return toText(value);
}

export function formatIntelValueWithRank(
  value: unknown,
  rank?: number,
  signed = false,
): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return formatIntelValue(value);
  }
  const absValue = signed ? Math.abs(value) : value;
  const base = formatIntelNumber(absValue, true);
  const withSign = signed ? (value >= 0 ? `+${base}` : `-${base}`) : base;
  if (typeof rank !== "number" || !Number.isFinite(rank)) return withSign;
  return `${withSign} (${Math.trunc(rank)})`;
}

function toRecordPart(value: unknown): number | null {
  const numeric = asNumber(value);
  if (numeric === null) return null;
  return Math.trunc(numeric);
}

export function formatTeamRecordWithRank(
  row: NflIntelResponseRow | undefined,
  rank?: number,
): string {
  if (!row) return "—";
  const wins = toRecordPart(row.wins);
  const losses = toRecordPart(row.losses);
  if (wins === null || losses === null) return "—";
  const ties = toRecordPart(row.ties) ?? 0;
  const record = ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
  if (typeof rank !== "number" || !Number.isFinite(rank)) return record;
  return `${record} (${Math.trunc(rank)})`;
}

export type NflIntelEndpoint =
  | "rosters"
  | "stats"
  | "standings"
  | "depth-charts"
  | "injuries"
  | "coaching";

export type NflCoachingCoverage = {
  team_count?: number;
  named_hc_count?: number;
  full_staff_count?: number;
  holes?: string[];
  thin_dc?: string[];
  source?: string;
  as_of?: string;
};

export type NflIntelCoachingResponse = NflIntelResponse & {
  coverage?: NflCoachingCoverage;
};

export async function fetchNflIntel(
  endpoint: NflIntelEndpoint,
  filters?: {
    season?: number;
    week?: number;
    team?: string;
  },
): Promise<NflIntelResponse> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return {
      season: null,
      week: null,
      team: null,
      count: 0,
      rows: [],
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const urlObj = new URL(`${base.replace(/\/+$/, "")}/nfl/intel/${endpoint}`);
  if (typeof filters?.season === "number") {
    urlObj.searchParams.set("season", String(filters.season));
  }
  if (typeof filters?.week === "number") {
    urlObj.searchParams.set("week", String(filters.week));
  }
  if (typeof filters?.team === "string" && filters.team.trim().length > 0) {
    urlObj.searchParams.set("team", filters.team.trim().toUpperCase());
  }
  const url = urlObj.toString();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(url, {
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!response.ok) {
      return {
        season: null,
        week: null,
        team: null,
        count: 0,
        rows: [],
        error: `Model service returned ${response.status}.`,
      };
    }
    const payload = (await response.json()) as Partial<NflIntelCoachingResponse>;
    return {
      season: typeof payload.season === "number" ? payload.season : null,
      week: typeof payload.week === "number" ? payload.week : null,
      team: typeof payload.team === "string" ? payload.team : null,
      count: typeof payload.count === "number" ? payload.count : 0,
      rows: Array.isArray(payload.rows) ? payload.rows : [],
      selection:
        payload.selection && typeof payload.selection === "object"
          ? payload.selection
          : undefined,
      error: typeof payload.error === "string" ? payload.error : undefined,
      ...(endpoint === "coaching" &&
      payload.coverage &&
      typeof payload.coverage === "object"
        ? { coverage: payload.coverage }
        : {}),
    };
  } catch {
    return {
      season: null,
      week: null,
      team: null,
      count: 0,
      rows: [],
      error: "Unable to reach model service.",
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchNflCoachingStaff(filters?: {
  season?: number;
  team?: string;
}): Promise<NflIntelCoachingResponse> {
  return fetchNflIntel("coaching", {
    season: filters?.season,
    team: filters?.team,
  }) as Promise<NflIntelCoachingResponse>;
}

export function coachingContinuityBadge(row: NflIntelResponseRow | null): {
  label: string;
  tone: "live" | "thin" | "unknown";
} {
  if (!row) return { label: "Unknown", tone: "unknown" };
  const status = typeof row.status === "string" ? row.status : "";
  const continuity =
    typeof row.continuity_label === "string" ? row.continuity_label : "";
  if (status === "thin" || status === "thin_dc") {
    return { label: "Thin", tone: "thin" };
  }
  if (continuity === "new_staff") return { label: "New staff", tone: "live" };
  if (continuity === "returning") return { label: "Returning", tone: "live" };
  if (continuity === "partial_change")
    return { label: "Staff change", tone: "live" };
  if (row.hc_name || row.oc_name || row.dc_name)
    return { label: "Named", tone: "live" };
  return { label: "Unknown", tone: "unknown" };
}

const CONFERENCE_ORDER: Record<string, number> = {
  AFC: 0,
  NFC: 1,
  Unknown: 2,
};

const DIVISION_ORDER: Record<string, number> = {
  East: 0,
  North: 1,
  South: 2,
  West: 3,
  Unknown: 4,
};

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asTeamCode(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toUpperCase();
  return normalized.length > 0 ? normalized : null;
}

function normalizeConference(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toUpperCase();
  if (normalized === "AFC" || normalized === "NFC") return normalized;
  return null;
}

function normalizeDivision(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim().toLowerCase();
  if (trimmed.length === 0) return null;
  const normalized = `${trimmed[0]?.toUpperCase() ?? ""}${trimmed.slice(1)}`;
  if (
    normalized === "East" ||
    normalized === "North" ||
    normalized === "South" ||
    normalized === "West"
  ) {
    return normalized;
  }
  return null;
}

function compareNullableNumbersDesc(
  left: number | null,
  right: number | null,
): number {
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  return right - left;
}

export function sortStandingsRows(
  rows: NflIntelResponseRow[],
): NflIntelResponseRow[] {
  const normalizedRows: NflIntelResponseRow[] = rows.map((row) => {
    const team = asTeamCode(row.team);
    const teamDirectoryEntry = resolveConferenceDivision(team);
    const conference =
      normalizeConference(row.conference) ??
      teamDirectoryEntry?.conference ??
      "Unknown";
    const division =
      normalizeDivision(row.division) ??
      teamDirectoryEntry?.division ??
      "Unknown";
    return {
      ...row,
      conference,
      division,
    } as NflIntelResponseRow;
  });
  return normalizedRows.sort((left, right) => {
    const conferenceDiff =
      (CONFERENCE_ORDER[left.conference as string] ?? 99) -
      (CONFERENCE_ORDER[right.conference as string] ?? 99);
    if (conferenceDiff !== 0) return conferenceDiff;
    const divisionDiff =
      (DIVISION_ORDER[left.division as string] ?? 99) -
      (DIVISION_ORDER[right.division as string] ?? 99);
    if (divisionDiff !== 0) return divisionDiff;
    const winsDiff = compareNullableNumbersDesc(
      asNumber(left["wins"]),
      asNumber(right["wins"]),
    );
    if (winsDiff !== 0) return winsDiff;
    const pctDiff = compareNullableNumbersDesc(
      asNumber(left["win_pct"]),
      asNumber(right["win_pct"]),
    );
    if (pctDiff !== 0) return pctDiff;
    const diffDiff = compareNullableNumbersDesc(
      asNumber(left["point_diff"]),
      asNumber(right["point_diff"]),
    );
    if (diffDiff !== 0) return diffDiff;
    return String(left["team"] ?? "").localeCompare(
      String(right["team"] ?? ""),
    );
  });
}

export function groupStandingsRows(rows: NflIntelResponseRow[]): Array<{
  conference: string;
  division: string;
  rows: NflIntelResponseRow[];
}> {
  const sorted = sortStandingsRows(rows);
  const groups: Array<{
    conference: string;
    division: string;
    rows: NflIntelResponseRow[];
  }> = [];
  for (const row of sorted) {
    const conference =
      typeof row.conference === "string" && row.conference.trim().length > 0
        ? row.conference
        : "Unknown";
    const division =
      typeof row.division === "string" && row.division.trim().length > 0
        ? row.division
        : "Unknown";
    const current = groups[groups.length - 1];
    if (
      !current ||
      current.conference !== conference ||
      current.division !== division
    ) {
      groups.push({ conference, division, rows: [row] });
      continue;
    }
    current.rows.push(row);
  }
  return groups;
}
