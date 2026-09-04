import "server-only";

import { env } from "@/lib/config/env";

/** Env-only Odds API keys. No embedded fallback constants. */
export function getOddsApiKeys(): string[] {
  return [
    ...new Set(
      [env.ODDS_API_KEY?.trim(), env.ODDS_API_KEY_BACKUP?.trim()].filter(
        (key): key is string => Boolean(key),
      ),
    ),
  ];
}
