import "server-only";

import { env } from "@/lib/config/env";

// Temporary server fallback until the higher-volume key is provisioned.
const EMBEDDED_ODDS_API_BACKUP_KEY = "90a633a22cbe3597b2bceab5eb665d48";

export function getOddsApiKeys(): string[] {
  return [
    ...new Set(
      [
        env.ODDS_API_KEY?.trim(),
        env.ODDS_API_KEY_BACKUP?.trim(),
        EMBEDDED_ODDS_API_BACKUP_KEY,
      ].filter((key): key is string => Boolean(key)),
    ),
  ];
}
