import { defineConfig } from "prisma/config";

// Fallback for build/CI when DATABASE_URL is not set (prisma generate only needs schema)
const databaseUrl =
  process.env.DATABASE_URL ?? "postgresql://build:build@localhost:5432/build";

export default defineConfig({
  schema: "prisma/schema.prisma",
  datasource: {
    url: databaseUrl,
  },
});
