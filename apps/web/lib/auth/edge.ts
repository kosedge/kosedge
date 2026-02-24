// apps/web/lib/auth/edge.ts
// NextAuth for Edge (middleware). Uses config without Node-only deps.
import NextAuth from "next-auth";
import { authConfigEdge } from "./config.edge";

export const auth = NextAuth(authConfigEdge);
