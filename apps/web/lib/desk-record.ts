import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export type DeskTicketResult = "W" | "L" | "P" | "OPEN";
export type DeskTicketGrade = "PLAY" | "LEAN";
export type DeskJuiceStatus = "stamped" | "DATA_GAP";

export type DeskRecordTicket = {
  ticket_id: string;
  sport: string;
  season: number;
  week: number;
  game: string;
  away: string;
  home: string;
  market: "spread" | "total";
  side: string;
  grade: DeskTicketGrade;
  line: number;
  juice: number | null;
  book: string | null;
  as_of: string | null;
  result: DeskTicketResult;
  stake_u: number;
  profit_u: number | null;
  juice_status: DeskJuiceStatus;
  final_away: number | null;
  final_home: number | null;
  source_package: string;
  notes?: string | null;
};

export type AtsTriple = { w: number; l: number; p: number };

export type DeskRoiSummary = {
  status: "ok" | "DATA_GAP" | "empty";
  profit_u: number | null;
  risked_u: number;
  roi: number | null;
  n_tickets: number;
  n_data_gap: number;
  n_stamped_juice: number;
  note?: string;
};

export type DeskRecordSummary = {
  sport: string;
  season: number;
  as_of: string;
  ledger_path: string;
  n_tickets: number;
  n_open: number;
  play_ats: AtsTriple;
  play_ats_str: string;
  lean_ats: AtsTriple;
  lean_ats_str: string;
  combined_ats: AtsTriple;
  combined_ats_str: string;
  combined_roi: DeskRoiSummary;
  open_ticket_ids: string[];
  tickets: DeskRecordTicket[];
};

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    const marker = path.join(current, "data", "desk-record");
    if (existsSync(marker)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

export function formatAts(t: AtsTriple): string {
  return `${t.w}-${t.l}-${t.p}`;
}

export function americanProfit(
  stake: number,
  juice: number,
  won: boolean,
): number {
  if (!won) return -stake;
  if (juice < 0) return stake * (100 / Math.abs(juice));
  return stake * (juice / 100);
}

function atsTriple(results: DeskTicketResult[]): AtsTriple {
  const t: AtsTriple = { w: 0, l: 0, p: 0 };
  for (const r of results) {
    if (r === "W") t.w += 1;
    else if (r === "L") t.l += 1;
    else if (r === "P") t.p += 1;
  }
  return t;
}

function parseTicket(raw: Record<string, unknown>): DeskRecordTicket | null {
  const result = raw.result;
  const grade = raw.grade;
  if (result !== "W" && result !== "L" && result !== "P" && result !== "OPEN") {
    return null;
  }
  if (grade !== "PLAY" && grade !== "LEAN") return null;
  const market = raw.market === "total" ? "total" : "spread";
  const juiceRaw = raw.juice;
  const juice =
    typeof juiceRaw === "number" && Number.isFinite(juiceRaw) ? juiceRaw : null;
  const juiceStatus: DeskJuiceStatus =
    juice != null && Math.abs(juice) >= 100 && raw.juice_status !== "DATA_GAP"
      ? "stamped"
      : "DATA_GAP";

  return {
    ticket_id: String(raw.ticket_id ?? ""),
    sport: String(raw.sport ?? ""),
    season: Number(raw.season),
    week: Number(raw.week),
    game: String(raw.game ?? ""),
    away: String(raw.away ?? ""),
    home: String(raw.home ?? ""),
    market,
    side: String(raw.side ?? ""),
    grade,
    line: Number(raw.line),
    juice,
    book: raw.book == null ? null : String(raw.book),
    as_of: raw.as_of == null ? null : String(raw.as_of),
    result,
    stake_u: Number(raw.stake_u ?? (grade === "LEAN" ? 0.5 : 1)),
    profit_u:
      typeof raw.profit_u === "number" && Number.isFinite(raw.profit_u)
        ? raw.profit_u
        : null,
    juice_status: juiceStatus,
    final_away:
      typeof raw.final_away === "number" ? raw.final_away : null,
    final_home:
      typeof raw.final_home === "number" ? raw.final_home : null,
    source_package: String(raw.source_package ?? ""),
    notes: raw.notes == null ? null : String(raw.notes),
  };
}

function loadTickets(sport: string, season: number): DeskRecordTicket[] {
  const root = findRepoRoot();
  if (!root) return [];
  const ledgerPath = path.join(
    root,
    "data",
    "desk-record",
    sport,
    String(season),
    "ledger.jsonl",
  );
  if (!existsSync(ledgerPath)) return [];
  const out: DeskRecordTicket[] = [];
  for (const line of readFileSync(ledgerPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const raw = JSON.parse(trimmed) as Record<string, unknown>;
      const ticket = parseTicket(raw);
      if (!ticket || !ticket.ticket_id) continue;
      out.push(ticket);
    } catch {
      // fail-closed: skip corrupt lines
    }
  }
  return out;
}

export function summarizeDeskTickets(
  tickets: DeskRecordTicket[],
  sport: string,
  season: number,
): DeskRecordSummary {
  const playSettled = tickets.filter(
    (t) => t.grade === "PLAY" && (t.result === "W" || t.result === "L" || t.result === "P"),
  );
  const leanSettled = tickets.filter(
    (t) => t.grade === "LEAN" && (t.result === "W" || t.result === "L" || t.result === "P"),
  );
  const openTickets = tickets.filter((t) => t.result === "OPEN");

  const playAts = atsTriple(playSettled.map((t) => t.result));
  const leanAts = atsTriple(leanSettled.map((t) => t.result));
  const combinedAts = atsTriple(
    [...playSettled, ...leanSettled].map((t) => t.result),
  );

  let profitSum = 0;
  let risked = 0;
  let roiTickets = 0;
  let dataGapRoi = 0;
  let stampedJuice = 0;

  for (const t of [...playSettled, ...leanSettled]) {
    if (t.result === "P") continue;
    if (t.juice == null || t.juice_status === "DATA_GAP" || Math.abs(t.juice) < 100) {
      dataGapRoi += 1;
      continue;
    }
    stampedJuice += 1;
    const won = t.result === "W";
    const profit =
      typeof t.profit_u === "number"
        ? t.profit_u
        : americanProfit(t.stake_u, t.juice, won);
    profitSum += profit;
    risked += t.stake_u;
    roiTickets += 1;
  }

  let combinedRoi: DeskRoiSummary;
  if (risked > 0) {
    combinedRoi = {
      status: "ok",
      profit_u: Number(profitSum.toFixed(6)),
      risked_u: Number(risked.toFixed(6)),
      roi: Number((profitSum / risked).toFixed(6)),
      n_tickets: roiTickets,
      n_data_gap: dataGapRoi,
      n_stamped_juice: stampedJuice,
    };
  } else if (dataGapRoi > 0) {
    combinedRoi = {
      status: "DATA_GAP",
      profit_u: null,
      risked_u: 0,
      roi: null,
      n_tickets: 0,
      n_data_gap: dataGapRoi,
      n_stamped_juice: stampedJuice,
      note: "Settled W/L tickets lack stamped pre-kick juice — no flat −110 invent.",
    };
  } else {
    combinedRoi = {
      status: "empty",
      profit_u: 0,
      risked_u: 0,
      roi: null,
      n_tickets: 0,
      n_data_gap: 0,
      n_stamped_juice: 0,
      note: "No settled W/L tickets with stake at risk yet.",
    };
  }

  return {
    sport,
    season,
    as_of: new Date().toISOString(),
    ledger_path: `data/desk-record/${sport}/${season}/ledger.jsonl`,
    n_tickets: tickets.length,
    n_open: openTickets.length,
    play_ats: playAts,
    play_ats_str: formatAts(playAts),
    lean_ats: leanAts,
    lean_ats_str: formatAts(leanAts),
    combined_ats: combinedAts,
    combined_ats_str: formatAts(combinedAts),
    combined_roi: combinedRoi,
    open_ticket_ids: openTickets.map((t) => t.ticket_id),
    tickets,
  };
}

export function loadDeskRecord(
  sport: string,
  season = 2026,
): DeskRecordSummary {
  const tickets = loadTickets(sport, season);
  return summarizeDeskTickets(tickets, sport, season);
}

export function formatSideLine(side: string, line: number): string {
  const abs = Math.abs(line);
  const signed = line > 0 ? `+${abs}` : line < 0 ? `−${abs}` : "PK";
  return `${side} ${signed}`;
}

export function formatJuice(juice: number | null, status: DeskJuiceStatus): string {
  if (status === "DATA_GAP" || juice == null) return "DATA GAP";
  const n = Math.round(juice);
  return n > 0 ? `+${n}` : String(n);
}
