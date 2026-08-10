/**
 * Edge Board desk voices — tone lenses, not personal bylines.
 * Stable hash(gameId) → same voice on refresh.
 */

export type DeskVoiceId =
  | "structural"
  | "market"
  | "script_pace"
  | "dog"
  | "totals";

export const DESK_VOICES: readonly DeskVoiceId[] = [
  "structural",
  "market",
  "script_pace",
  "dog",
  "totals",
] as const;

export function stableGameHash(gameId: string): number {
  const s = String(gameId || "");
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function pickDeskVoice(gameId: string): DeskVoiceId {
  const idx = stableGameHash(gameId) % DESK_VOICES.length;
  return DESK_VOICES[idx]!;
}

/** Internal voice label for tests / debug — never shown as a byline on cards. */
export function deskVoiceLabel(voice: DeskVoiceId): string {
  switch (voice) {
    case "structural":
      return "Structural desk";
    case "market":
      return "Market desk";
    case "script_pace":
      return "Script / pace desk";
    case "dog":
      return "Dog desk";
    case "totals":
      return "Totals desk";
  }
}
