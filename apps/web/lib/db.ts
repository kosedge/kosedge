// apps/web/lib/db.ts
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "#prisma";

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

// Prisma 7 "client" engine requires adapter or accelerateUrl (https://pris.ly/d/client-constructor)
const connectionString = process.env.DATABASE_URL;
const hasDatabaseUrl = typeof connectionString === "string" && connectionString.length > 0;

function createMissingDatabaseProxy(): PrismaClient {
  return new Proxy(
    {},
    {
      get() {
        throw new Error(
          "DATABASE_URL is required at runtime for Prisma operations."
        );
      },
    }
  ) as PrismaClient;
}

const prismaClient =
  hasDatabaseUrl
    ? globalForPrisma.prisma ??
      new PrismaClient({
        adapter: new PrismaPg({ connectionString: connectionString as string }),
        log:
          process.env.NODE_ENV === "development"
            ? ["query", "error", "warn"]
            : ["error"],
      })
    : createMissingDatabaseProxy();

export const prisma = prismaClient;

if (hasDatabaseUrl && process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}

// Graceful shutdown
if (hasDatabaseUrl && typeof process !== "undefined") {
  process.on("beforeExit", async () => {
    await prisma.$disconnect();
  });
}
