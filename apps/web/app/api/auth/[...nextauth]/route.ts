// apps/web/app/api/auth/[...nextauth]/route.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { handlers } from "@/lib/auth";

async function withJsonError(
  handler: (req: NextRequest) => Promise<Response>,
  req: NextRequest,
) {
  try {
    return await handler(req);
  } catch (e) {
    // Ensure Auth.js errors return JSON so the client never sees HTML ("Unexpected token '<'")
    return NextResponse.json(
      {
        error: "AuthError",
        message: e instanceof Error ? e.message : "Authentication failed",
      },
      { status: 500 },
    );
  }
}

export const GET = (req: NextRequest) => withJsonError(handlers.GET, req);
export const POST = (req: NextRequest) => withJsonError(handlers.POST, req);
