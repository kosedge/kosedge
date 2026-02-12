// apps/web/src/config/env.ts
import { z } from "zod";

const EnvSchema = z.object({
  MODEL_SERVICE_URL: z.string().url(),
  INTERNAL_API_SECRET: z.string().min(16).optional(),
  NODE_ENV: z.enum(["development", "test", "production"]).optional(),
});

export const env = EnvSchema.parse(process.env);