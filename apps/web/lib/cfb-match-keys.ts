/**
 * CFB Odds ↔ KEI name matching.
 * Folds accents (José/Jose), apostrophes (Hawai'i), and common aliases
 * so published KEI rows are not dropped off the Week 0/1 tabs.
 */

const ALIASES: Record<string, string> = {
  hawaii: "hawaii",
  "hawai'i": "hawaii",
  hawaiʻi: "hawaii",
  haw: "hawaii",
  "rainbow warriors": "hawaii",
  "san jose": "san jose",
  "san josé": "san jose",
  sjsu: "san jose",
  "jose state": "san jose",
};

export function foldCfbName(raw: string): string {
  return String(raw || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[''`ʻ]/g, "")
    .replace(/[^a-z0-9@\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function aliasToken(s: string): string {
  const folded = foldCfbName(s);
  return ALIASES[folded] ?? folded;
}

export function cfbGameMatchKeys(game: string): string[] {
  const n = foldCfbName(game).replace(/\s*@\s*/g, " @ ");
  const parts = n.split(/\s*@\s*/);
  if (parts.length !== 2) return n ? [n] : [];
  const away = aliasToken(parts[0] ?? "");
  const home = aliasToken(parts[1] ?? "");
  const take = (s: string, words: number) =>
    s.split(/\s+/).filter(Boolean).slice(0, words).join(" ");
  const keys = [
    `${away} @ ${home}`,
    `${take(away, 2)} @ ${take(home, 2)}`,
    `${take(away, 1)} @ ${take(home, 1)}`,
  ];
  return [...new Set(keys.filter((k) => k.includes("@")))];
}

export function cfbGamesMatch(a: string, b: string): boolean {
  const left = new Set(cfbGameMatchKeys(a));
  return cfbGameMatchKeys(b).some((k) => left.has(k));
}
