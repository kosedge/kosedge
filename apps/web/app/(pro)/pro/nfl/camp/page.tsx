import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

/**
 * Legacy Camp Desk URL. Canonical live route is /pro/nfl/club.
 * next.config also redirects; this covers app-router navigations.
 */
export default function NflCampDeskRedirectPage() {
  redirect("/pro/nfl/club");
}
