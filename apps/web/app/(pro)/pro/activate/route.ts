import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Temporary Pro activation for testing: sets cookies and redirects to /pro/welcome.
 * Does not drive subscription entitlement (isProUser() uses DB only).
 * Replace with real auth + Stripe webhook-driven entitlement for production.
 */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const plan = url.searchParams.get("plan") ?? "monthly";

  const res = NextResponse.redirect(new URL("/pro/welcome", url.origin), 302);

  res.cookies.set("kosedge_pro", "1", {
    path: "/",
    httpOnly: false,
    sameSite: "lax",
  });

  res.cookies.set("kosedge_pro_plan", plan, {
    path: "/",
    httpOnly: false,
    sameSite: "lax",
  });

  return res;
}
