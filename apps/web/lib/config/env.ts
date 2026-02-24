// apps/web/lib/config/env.ts
import { z } from "zod";

const EnvSchema = z.object({
  // Edge board proxy: optional in dev if no upstream model service
  MODEL_SERVICE_URL: z.string().url().optional(),
  INTERNAL_API_SECRET: z.string().min(16).optional(),
  // Odds API fallback for NCAAM (free tier: 500 req/mo)
  ODDS_API_KEY: z.string().min(1).optional(),
  // Widget embed (server-only; never exposed to client)
  ODDS_WIDGET_ACCESS_KEY: z.string().min(1).optional(),
  NODE_ENV: z.enum(["development", "test", "production"]).optional(),

  // Authentication
  AUTH_SECRET: z.string().min(32).optional(),
  AUTH_URL: z.string().url().optional(),
  DATABASE_URL: z.string().url().optional(),
  
  // OAuth Providers (optional - add as needed)
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  GITHUB_CLIENT_ID: z.string().optional(),
  GITHUB_CLIENT_SECRET: z.string().optional(),
  
  // Error Tracking (optional)
  NEXT_PUBLIC_SENTRY_DSN: z.string().url().optional(),
  SENTRY_AUTH_TOKEN: z.string().optional(),
  
  // Logging
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).optional(),
  
  // Redis (optional)
  REDIS_URL: z.string().url().optional(),
});

export const env = EnvSchema.parse(process.env);
