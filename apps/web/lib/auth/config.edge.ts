// apps/web/lib/auth/config.edge.ts
// Edge-safe config for middleware only. No Node.js modules (bcryptjs, prisma).
import type { JWT } from "next-auth/jwt";
import type { Session, User } from "next-auth";
import type { UserRole } from "@/src/generated/prisma";

export const authConfigEdge = {
  providers: [], // Edge config: providers live in auth/config.ts (Node-only)
  session: {
    strategy: "jwt" as const,
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },
  callbacks: {
    jwt({
      token,
      user,
    }: {
      token: JWT;
      user?: User;
    }) {
      if (user) {
        token.id = user.id;
        token.role = ((user as { role?: string }).role ?? "USER") as JWT["role"];
      }
      return token;
    },
    session({
      session,
      token,
    }: {
      session: Session;
      token: JWT;
    }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as UserRole;
      }
      return session;
    },
  },
};
