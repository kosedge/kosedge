#!/usr/bin/env node
/**
 * Generate sample kei_lines_ncaam.json for the next 7 days (ET).
 * Run from apps/web: node scripts/populate-kei-lines-sample.js
 * Output: data/processed/kei_lines_ncaam.json
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const ET = "America/New_York";
/** Today's date in ET as { year, month, day }. */
function todayET() {
  const s = new Date().toLocaleDateString("en-CA", { timeZone: ET });
  const [y, m, day] = s.split("-").map(Number);
  return { year: y, month: m, day };
}
/** Add n days to a { year, month, day } in ET (naive calendar add). */
function addDays(y, m, day, n) {
  const d = new Date(Date.UTC(y, m - 1, day + n, 12, 0, 0));
  return {
    year: d.getUTCFullYear(),
    month: d.getUTCMonth() + 1,
    day: d.getUTCDate(),
  };
}
// 7 PM ET on (year, month, day) = midnight UTC next day (EST)
function toISO7PMET(year, month, day) {
  const d = new Date(Date.UTC(year, month - 1, day, 24, 0, 0));
  return d.toISOString();
}
// 9 PM ET
function toISO9PMET(year, month, day) {
  const d = new Date(Date.UTC(year, month - 1, day, 26, 0, 0));
  return d.toISOString();
}

const TEAMS = [
  ["Duke", "North Carolina"],
  ["Kansas", "Texas"],
  ["Kentucky", "Tennessee"],
  ["UConn", "Villanova"],
  ["Houston", "Baylor"],
  ["Arizona", "UCLA"],
  ["Purdue", "Indiana"],
  ["Marquette", "Creighton"],
  ["Alabama", "Auburn"],
  ["Iowa State", "Kansas State"],
];

const outDir = path.join(__dirname, "..", "data", "processed");
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

const today = todayET();
const games = [];
let id = 1;
for (let i = 0; i < 7; i++) {
  const d = addDays(today.year, today.month, today.day, i);
  const { year: y, month: m, day } = d;
  const [away, home] = TEAMS[i % TEAMS.length];
  const spread = (Math.random() * 12 - 4).toFixed(1);
  const total = (140 + Math.random() * 20).toFixed(1);
  games.push({
    id: `sample-${id++}`,
    homeTeam: home,
    awayTeam: away,
    commenceTime: toISO7PMET(y, m, day),
    projSpreadHome: parseFloat(spread),
    projTotal: parseFloat(total),
  });
  if (i % 2 === 0) {
    const [a2, h2] = TEAMS[(i + 3) % TEAMS.length];
    games.push({
      id: `sample-${id++}`,
      homeTeam: h2,
      awayTeam: a2,
      commenceTime: toISO9PMET(y, m, day),
      projSpreadHome: parseFloat((Math.random() * 10 - 3).toFixed(1)),
      projTotal: parseFloat((145 + Math.random() * 15).toFixed(1)),
    });
  }
}

const outPath = path.join(outDir, "kei_lines_ncaam.json");
fs.writeFileSync(outPath, JSON.stringify({ games }, null, 2), "utf8");
console.log("Wrote", outPath, "with", games.length, "games.");
