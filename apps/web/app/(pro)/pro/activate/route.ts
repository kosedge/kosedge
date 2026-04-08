import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * TEMP Pro activation:
 * - Sets cookies to simulate an active Pro user.
 * - Redirects to /pro/welcome
 *
 * Later: replace this with real auth + Stripe webhook-driven entitlement.
 */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const plan = url.searchParams.get("plan") ?? "monthly"; // weekly | monthly | yearly

  const res = NextResponse.redirect(new URL("/pro/welcome", url.origin), 302);

  // Gate cookie (your existing logic checks this)
  res.cookies.set("kosedge_pro", "1", {
    path: "/",
    httpOnly: false, // TEMP so you can see it easily; later set true
    sameSite: "lax",
  });

  // Optional: remember which plan they picked (useful later)
  res.cookies.set("kosedge_pro_plan", plan, {
    path: "/",
    httpOnly: false,
    sameSite: "lax",
  });

  return res;
}
