// apps/web/__tests__/setup/db.ts
import { PrismaClient } from "@/src/generated/prisma";
import { execSync } from "child_process";
import { randomBytes } from "crypto";

const generateDatabaseURL = () => {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL environment variable is not set");
  }

  const url = new URL(process.env.DATABASE_URL);
  const testDbName = `test_${randomBytes(8).toString("hex")}`;
  url.pathname = `/${testDbName}`;

  return { url: url.toString(), dbName: testDbName };
};

export const setupTestDatabase = async () => {
  const { url, dbName } = generateDatabaseURL();

  // Create test database
  execSync(`psql ${process.env.DATABASE_URL} -c "CREATE DATABASE ${dbName};"`, {
    stdio: "inherit",
  });

  // Run migrations
  execSync(`DATABASE_URL="${url}" pnpm prisma migrate deploy`, {
    stdio: "inherit",
  });

  const prisma = new PrismaClient({
    datasources: {
      db: {
        url,
      },
    },
  });

  return { prisma, dbName, url };
};

export const teardownTestDatabase = async (dbName: string) => {
  // Drop test database
  execSync(`psql ${process.env.DATABASE_URL} -c "DROP DATABASE ${dbName};"`, {
    stdio: "inherit",
  });
};
