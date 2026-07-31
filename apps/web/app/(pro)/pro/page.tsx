import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

/** Primary Pro entry → NFL research desk (UI overhaul), not the legacy multi-sport welcome. */
export default async function ProPage() {
  redirect("/pro/nfl/overview");
}
