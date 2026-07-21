/**
 * Sportsbook display metadata for Edge Board best-line chips.
 * Keys match The Odds API bookmaker keys.
 */

export type SportsbookMeta = {
  key: string;
  name: string;
  short: string;
  homepage: string;
  /** Tailwind-friendly chip colors */
  chipClass: string;
};

const SPORTSBOOKS: Record<string, SportsbookMeta> = {
  draftkings: {
    key: "draftkings",
    name: "DraftKings",
    short: "DK",
    homepage: "https://www.draftkings.com",
    chipClass: "bg-emerald-500/20 text-emerald-300 border-emerald-400/35",
  },
  fanduel: {
    key: "fanduel",
    name: "FanDuel",
    short: "FD",
    homepage: "https://www.fanduel.com",
    chipClass: "bg-blue-500/20 text-blue-300 border-blue-400/35",
  },
  betmgm: {
    key: "betmgm",
    name: "BetMGM",
    short: "MGM",
    homepage: "https://sports.betmgm.com",
    chipClass: "bg-amber-500/20 text-amber-200 border-amber-400/35",
  },
  bet365: {
    key: "bet365",
    name: "Bet365",
    short: "365",
    homepage: "https://www.bet365.com",
    chipClass: "bg-lime-500/20 text-lime-200 border-lime-400/35",
  },
  fanatics: {
    key: "fanatics",
    name: "Fanatics",
    short: "FAN",
    homepage: "https://sportsbook.fanatics.com",
    chipClass: "bg-rose-500/20 text-rose-200 border-rose-400/35",
  },
  betrivers: {
    key: "betrivers",
    name: "BetRivers",
    short: "BR",
    homepage: "https://www.betrivers.com",
    chipClass: "bg-sky-500/20 text-sky-200 border-sky-400/35",
  },
  hardrockbet: {
    key: "hardrockbet",
    name: "Hard Rock Bet",
    short: "HR",
    homepage: "https://www.hardrock.bet",
    chipClass: "bg-orange-500/20 text-orange-200 border-orange-400/35",
  },
  circa: {
    key: "circa",
    name: "Circa",
    short: "CIR",
    homepage: "https://www.circasports.com",
    chipClass: "bg-violet-500/20 text-violet-200 border-violet-400/35",
  },
  betr: {
    key: "betr",
    name: "Betr",
    short: "BTR",
    homepage: "https://www.betr.app",
    chipClass: "bg-fuchsia-500/20 text-fuchsia-200 border-fuchsia-400/35",
  },
  /** Consensus / fair-lines market average when no single book wins. */
  market: {
    key: "market",
    name: "Market",
    short: "MKT",
    homepage: "",
    chipClass: "bg-white/10 text-gray-300 border-white/20",
  },
  /** Kosedge provisional Open/Best when Vegas has not posted yet. */
  keinfl: {
    key: "keinfl",
    name: "KEINFL",
    short: "KEI",
    homepage: "/pro/nfl/fair-lines",
    chipClass: "bg-kos-gold/20 text-kos-gold border-kos-gold/35",
  },
};

const BY_NAME = new Map(
  Object.values(SPORTSBOOKS).map((b) => [b.name.toLowerCase(), b] as const),
);

export function getSportsbook(bookOrKey: string | undefined | null): SportsbookMeta | null {
  if (!bookOrKey) return null;
  const raw = bookOrKey.trim();
  if (!raw) return null;
  const byKey = SPORTSBOOKS[raw.toLowerCase()];
  if (byKey) return byKey;
  return BY_NAME.get(raw.toLowerCase()) ?? null;
}

export function sportsbookHomepage(bookOrKey: string | undefined | null): string | null {
  return getSportsbook(bookOrKey)?.homepage ?? null;
}
