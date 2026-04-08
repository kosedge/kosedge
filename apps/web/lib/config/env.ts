// apps/web/lib/config/env.ts
import { z } from "zod";

const optionalString = z.preprocess(
  (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
  z.string().optional()
);
const optionalUrl = z.preprocess(
  (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
  z.string().url().optional()
);

const EnvSchema = z.object({
  // Edge board proxy: optional in dev if no upstream model service
  MODEL_SERVICE_URL: optionalUrl,
  INTERNAL_API_SECRET: z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.string().min(16).optional()
  ),
  // Odds API fallback for NCAAM (free tier: 500 req/mo)
  ODDS_API_KEY: optionalString,
  ODDS_API_KEY_BACKUP: optionalString,
  // Widget embed (server-only; never exposed to client)
  ODDS_WIDGET_ACCESS_KEY: optionalString,
  NODE_ENV: z.enum(["development", "test", "production"]).optional(),

  // Authentication
  AUTH_SECRET: z.preprocess(
    (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
    z.string().min(32).optional()
  ),
  AUTH_URL: optionalUrl,
  DATABASE_URL: optionalUrl,
  
  // OAuth Providers (optional - add as needed)
  GOOGLE_CLIENT_ID: optionalString,
  GOOGLE_CLIENT_SECRET: optionalString,
  GITHUB_CLIENT_ID: optionalString,
  GITHUB_CLIENT_SECRET: optionalString,
  
  // Error Tracking (optional)
  NEXT_PUBLIC_SENTRY_DSN: optionalUrl,
  SENTRY_AUTH_TOKEN: optionalString,
  
  // Logging
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).optional(),
  
  // Redis (optional)
  REDIS_URL: optionalUrl,
  SITE_URL: optionalUrl,
});

export const env = EnvSchema.parse(process.env);
