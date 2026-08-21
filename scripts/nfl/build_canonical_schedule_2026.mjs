#!/usr/bin/env node
/**
 * One-shot: parse NFL Football Operations 2026 REG table → canonical JSON.
 * Source dump: pass path as argv[1].
 */
import fs from "node:fs";
import path from "node:path";

const NAMES = {
  "Arizona Cardinals": "ARI",
  "Atlanta Falcons": "ATL",
  "Baltimore Ravens": "BAL",
  "Buffalo Bills": "BUF",
  "Carolina Panthers": "CAR",
  "Chicago Bears": "CHI",
  "Cincinnati Bengals": "CIN",
  "Cleveland Browns": "CLE",
  "Dallas Cowboys": "DAL",
  "Denver Broncos": "DEN",
  "Detroit Lions": "DET",
  "Green Bay Packers": "GB",
  "Houston Texans": "HOU",
  "Indianapolis Colts": "IND",
  "Jacksonville Jaguars": "JAX",
  "Kansas City Chiefs": "KC",
  "Las Vegas Raiders": "LV",
  "Los Angeles Chargers": "LAC",
  "Los Angeles Rams": "LAR",
  "Miami Dolphins": "MIA",
  "Minnesota Vikings": "MIN",
  "New England Patriots": "NE",
  "New Orleans Saints": "NO",
  "New York Giants": "NYG",
  "New York Jets": "NYJ",
  "Philadelphia Eagles": "PHI",
  "Pittsburgh Steelers": "PIT",
  "San Francisco 49ers": "SF",
  "Seattle Seahawks": "SEA",
  "Tampa Bay Buccaneers": "TB",
  "Tennessee Titans": "TEN",
  "Washington Commanders": "WAS",
};

const STADIUMS = {
  ARI: { venue: "State Farm Stadium", city: "Glendale" },
  ATL: { venue: "Mercedes-Benz Stadium", city: "Atlanta" },
  BAL: { venue: "M&T Bank Stadium", city: "Baltimore" },
  BUF: { venue: "Highmark Stadium", city: "Orchard Park" },
  CAR: { venue: "Bank of America Stadium", city: "Charlotte" },
  CHI: { venue: "Soldier Field", city: "Chicago" },
  CIN: { venue: "Paycor Stadium", city: "Cincinnati" },
  CLE: { venue: "Huntington Bank Field", city: "Cleveland" },
  DAL: { venue: "AT&T Stadium", city: "Arlington" },
  DEN: { venue: "Empower Field at Mile High", city: "Denver" },
  DET: { venue: "Ford Field", city: "Detroit" },
  GB: { venue: "Lambeau Field", city: "Green Bay" },
  HOU: { venue: "NRG Stadium", city: "Houston" },
  IND: { venue: "Lucas Oil Stadium", city: "Indianapolis" },
  JAX: { venue: "EverBank Stadium", city: "Jacksonville" },
  KC: { venue: "GEHA Field at Arrowhead Stadium", city: "Kansas City" },
  LAC: { venue: "SoFi Stadium", city: "Inglewood" },
  LAR: { venue: "SoFi Stadium", city: "Inglewood" },
  LV: { venue: "Allegiant Stadium", city: "Las Vegas" },
  MIA: { venue: "Hard Rock Stadium", city: "Miami Gardens" },
  MIN: { venue: "U.S. Bank Stadium", city: "Minneapolis" },
  NE: { venue: "Gillette Stadium", city: "Foxborough" },
  NO: { venue: "Caesars Superdome", city: "New Orleans" },
  NYG: { venue: "MetLife Stadium", city: "East Rutherford" },
  NYJ: { venue: "MetLife Stadium", city: "East Rutherford" },
  PHI: { venue: "Lincoln Financial Field", city: "Philadelphia" },
  PIT: { venue: "Acrisure Stadium", city: "Pittsburgh" },
  SEA: { venue: "Lumen Field", city: "Seattle" },
  SF: { venue: "Levi's Stadium", city: "Santa Clara" },
  TB: { venue: "Raymond James Stadium", city: "Tampa" },
  TEN: { venue: "Nissan Stadium", city: "Nashville" },
  WAS: { venue: "Northwest Stadium", city: "Landover" },
};

const INTL = {
  Melbourne: { venue: "Melbourne Cricket Ground", city: "Melbourne" },
  "Rio de Janeiro": { venue: "Maracanã Stadium", city: "Rio de Janeiro" },
  Tottenham: { venue: "Tottenham Hotspur Stadium", city: "London" },
  Wembley: { venue: "Wembley Stadium", city: "London" },
  Paris: { venue: "Stade de France", city: "Paris" },
  Madrid: { venue: "Bernabéu Stadium", city: "Madrid" },
  Munich: { venue: "FC Bayern Munich Arena", city: "Munich" },
  "Mexico City": { venue: "Estadio Banorte", city: "Mexico City" },
};

const MONTHS = {
  Jan: 1,
  January: 1,
  Sept: 9,
  September: 9,
  Oct: 10,
  October: 10,
  Nov: 11,
  November: 11,
  Dec: 12,
  December: 12,
};

function pad(n) {
  return String(n).padStart(2, "0");
}

function nyOffset(ymd) {
  const probe = new Date(`${ymd}T18:00:00Z`);
  const tz = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    timeZoneName: "short",
  })
    .formatToParts(probe)
    .find((p) => p.type === "timeZoneName")?.value;
  return tz === "EDT" ? "-04:00" : "-05:00";
}

function toUtcIso(year, month, day, hour, minute) {
  const ymd = `${year}-${pad(month)}-${pad(day)}`;
  const local = `${ymd}T${pad(hour)}:${pad(minute)}:00${nyOffset(ymd)}`;
  return new Date(local).toISOString();
}

function parseClock(raw) {
  const t = String(raw || "").trim().replace(/\*$/, "");
  if (!t || t.toUpperCase() === "TBD") return null;
  const m = t.match(/^(\d{1,2}):(\d{2})\s*([ap])$/i);
  if (!m) return null;
  let hour = Number(m[1]) % 12;
  if (m[3].toLowerCase() === "p") hour += 12;
  return { hour, minute: Number(m[2]) };
}

function parseDateLine(line, defaultYear) {
  const m = line.match(
    /^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(Jan|January|Sept|September|Oct|October|Nov|November|Dec|December)\.?\s+(\d{1,2}),\s+(\d{4})/i,
  );
  if (!m) return null;
  return {
    month: MONTHS[m[2]],
    day: Number(m[3]),
    year: Number(m[4]),
  };
}

function parseTeam(name) {
  const clean = name.replace(/\s+\([^)]+\)\s*$/, "").trim();
  return NAMES[clean] || null;
}

function parseMatchup(cell) {
  const raw = cell.trim();
  if (raw === "TBD") return null;
  const intl = raw.match(/\(([^)]+)\)\s*$/);
  const hostHint = intl ? intl[1].trim() : null;
  const vs = raw.match(/^(.+?)\s+vs\.?\s+(.+)$/i);
  const at = raw.match(/^(.+?)\s+at\s+(.+)$/i);
  if (vs) {
    const away = parseTeam(vs[1]);
    const home = parseTeam(vs[2]);
    if (!away || !home) return null;
    return { away, home, neutral: true, hostHint };
  }
  if (at) {
    const away = parseTeam(at[1]);
    const home = parseTeam(at[2]);
    if (!away || !home) return null;
    return { away, home, neutral: false, hostHint };
  }
  return null;
}

function engineAbbr(abbr) {
  return abbr === "LAR" ? "LA" : abbr;
}

function gameId(season, week, away, home) {
  return `${season}-W${pad(week)}-${engineAbbr(away)}@${engineAbbr(home)}`;
}

function productGameId(season, week, away, home) {
  return `${season}-W${pad(week)}-${away}@${home}`;
}

const src = process.argv[2];
if (!src) {
  console.error("usage: build_canonical_schedule_2026.mjs <ops-markdown>");
  process.exit(1);
}
const text = fs.readFileSync(src, "utf8");
const lines = text.split(/\r?\n/);

let week = null;
let date = null;
const games = new Map();

for (const line of lines) {
  const weekHit = line.match(/^WEEK\s+(\d+)/i);
  if (weekHit) {
    week = Number(weekHit[1]);
    date = null;
    continue;
  }
  if (/^Date TBD/i.test(line.trim())) {
    date = null;
    continue;
  }
  const parsedDate = parseDateLine(line.trim());
  if (parsedDate) {
    date = parsedDate;
    continue;
  }
  const row = line.match(/^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|/);
  if (!row || !week) continue;
  const matchup = parseMatchup(row[1]);
  if (!matchup) continue;
  const clock = parseClock(row[2]);
  const network = row[3].replace(/\*$/, "").trim();
  const kickoffUtc =
    date && clock
      ? toUtcIso(date.year, date.month, date.day, clock.hour, clock.minute)
      : null;
  const intl = matchup.hostHint ? INTL[matchup.hostHint] : null;
  const site = matchup.neutral
    ? intl || { venue: matchup.hostHint, city: matchup.hostHint }
    : STADIUMS[matchup.home];
  const gid = gameId(2026, week, matchup.away, matchup.home);
  games.set(gid, {
    game_id: productGameId(2026, week, matchup.away, matchup.home),
    engine_game_id: gid,
    season: 2026,
    week,
    game_type: "REG",
    away_team_id: matchup.away,
    home_team_id: matchup.home,
    venue: site?.venue || null,
    location: site?.city || null,
    international: Boolean(matchup.neutral || intl),
    kickoff_utc: kickoffUtc,
    network: network === "TBD" ? null : network,
    status: kickoffUtc ? "scheduled" : "time_tbd",
  });
}

const list = [...games.values()].sort((a, b) =>
  a.engine_game_id.localeCompare(b.engine_game_id),
);

const out = {
  season: 2026,
  game_type: "REG",
  source: "nfl-football-operations-2026-regular-season-schedule",
  source_url:
    "https://operations.nfl.com/calendar-events/nfl-schedule/2026-regular-season-schedule/",
  as_of: "2026-08-21",
  notes:
    "kickoff_utc is display SoT (derived from published ET). Odds commence may differ; canonical wins for product display. Weeks 16–18 include flex TBD kickoffs.",
  game_count: list.length,
  games: list,
};

const dest = path.resolve(
  "apps/web/lib/nfl-canonical-schedule-2026.json",
);
fs.writeFileSync(dest, `${JSON.stringify(out, null, 2)}\n`);
console.log(`wrote ${list.length} games → ${dest}`);
const w1 = list.filter((g) => g.week === 1);
console.log(`week 1: ${w1.length}`);
for (const g of w1) {
  console.log(
    `${g.game_id} ${g.kickoff_utc} ${g.venue} ${g.location}`,
  );
}
