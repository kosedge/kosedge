/**
 * CFB Odds ↔ KEI name matching.
 * Folds accents (José/Jose), apostrophes (Hawai'i), and common aliases
 * so published KEI rows are not dropped off the Week 0/1 tabs.
 *
 * Miami OH vs Miami FL must never collapse to the same take(1) token.
 * Bare "miami" is intentionally NOT aliased (ambiguous).
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

  // Massachusetts / UMass (Odds: UMass Minutemen · slate: Massachusetts Minutemen)
  umass: "massachusetts",
  "umass minutemen": "massachusetts minutemen",
  massachusetts: "massachusetts",
  "massachusetts minutemen": "massachusetts minutemen",
  mass: "massachusetts",

  // Miami FL vs Miami OH — distinct first tokens after alias
  "miami oh": "miami-ohio",
  "miami ohio": "miami-ohio",
  "miami oh redhawks": "miami-ohio redhawks",
  "miami ohio redhawks": "miami-ohio redhawks",
  "m-oh": "miami-ohio",
  moh: "miami-ohio",
  "miami fl": "miami-florida",
  "miami florida": "miami-florida",
  "miami hurricanes": "miami-florida hurricanes",
  "miami florida hurricanes": "miami-florida hurricanes",
  mia: "miami-florida",

  // Common abbr / book short names used on join keys
  rut: "rutgers",
  pitt: "pittsburgh",
  "ole miss": "mississippi",
  "southern cal": "usc",
  "texas am": "texas a m",
  "texas a m": "texas a m",
  tamu: "texas a m",
  uconn: "connecticut",
  conn: "connecticut",
  "app state": "appalachian state",
  fau: "florida atlantic",
  fiu: "florida international",
  utsa: "texas san antonio",
  "southern miss": "southern mississippi",
  usm: "southern mississippi",
  mtsu: "middle tennessee",
  "middle tennessee": "middle tennessee",
  wku: "western kentucky",
  "western kentucky": "western kentucky",
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
  if (!folded) return folded;
  if (ALIASES[folded]) return ALIASES[folded];

  const words = folded.split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    const two = `${words[0]} ${words[1]}`;
    if (ALIASES[two]) {
      const rest = words.slice(2).join(" ");
      return rest ? `${ALIASES[two]} ${rest}` : ALIASES[two]!;
    }
  }
  if (words.length >= 1 && ALIASES[words[0]!]) {
    const head = ALIASES[words[0]!]!;
    const rest = words.slice(1).join(" ");
    return rest ? `${head} ${rest}` : head;
  }
  return folded;
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
