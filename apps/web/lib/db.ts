// apps/web/lib/db.ts
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "#prisma";

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

// Prisma 7 "client" engine requires adapter or accelerateUrl (https://pris.ly/d/client-constructor)
const connectionString =
  process.env.DATABASE_URL ?? "postgresql://localhost:5432/placeholder";
const adapter = new PrismaPg({ connectionString });

const prismaOptions: ConstructorParameters<typeof PrismaClient>[0] = {
  adapter,
  log:
    process.env.NODE_ENV === "development"
      ? ["query", "error", "warn"]
      : ["error"],
};

export const prisma = globalForPrisma.prisma ?? new PrismaClient(prismaOptions);

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

// Graceful shutdown
if (typeof process !== "undefined") {
  process.on("beforeExit", async () => {
    await prisma.$disconnect();
  });
}
