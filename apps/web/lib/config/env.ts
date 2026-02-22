// apps/web/lib/config/env.ts
import { z } from "zod";

/** Coerce empty env strings to undefined so Zod optional() works (e.g. Vercel env vars). */
const optionalString = (schema: z.ZodString) =>
  z.preprocess(
    (v) => (v === "" || v === null ? undefined : v),
    schema.optional(),
  );

const EnvSchema = z.object({
  MODEL_SERVICE_URL: optionalString(z.string().url()),
  INTERNAL_API_SECRET: optionalString(z.string().min(16)),
  ODDS_API_KEY: optionalString(z.string().min(1)),
  ODDS_API_KEY_BACKUP: optionalString(z.string().min(1)),
  ODDS_WIDGET_ACCESS_KEY: optionalString(z.string().min(1)),
  NODE_ENV: z.enum(["development", "test", "production"]).optional(),

  AUTH_SECRET: optionalString(z.string().min(32)),
  AUTH_URL: optionalString(z.string().url()),
  DATABASE_URL: optionalString(z.string().url()),

  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  GITHUB_CLIENT_ID: z.string().optional(),
  GITHUB_CLIENT_SECRET: z.string().optional(),

  NEXT_PUBLIC_SENTRY_DSN: optionalString(z.string().url()),
  SENTRY_AUTH_TOKEN: z.string().optional(),

  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).optional(),

  REDIS_URL: optionalString(z.string().url()),
});

export const env = EnvSchema.parse(process.env);
