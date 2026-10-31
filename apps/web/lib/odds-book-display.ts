/**
 * Client-safe book labels. No Odds HTTP, no odds-acquire, no Node builtins.
 * Keep paid acquire on the server (`lib/odds-api.ts` → `lib/odds-acquire`).
 */

const BOOK_DISPLAY: Record<string, string> = {
  draftkings: "DraftKings",
  fanduel: "FanDuel",
  circa: "Circa",
  hardrockbet: "Hard Rock Bet",
  betmgm: "BetMGM",
  bet365: "Bet365",
  fanatics: "Fanatics",
  betrivers: "BetRivers",
  betr: "Betr",
  bovada: "Bovada",
  williamhill_us: "Caesars",
  betonlineag: "BetOnline",
};

export function bookDisplay(key: string): string {
  return BOOK_DISPLAY[key.toLowerCase()] ?? key;
}
