import { redirect } from "next/navigation";

/**
 * Bookmark / typed alias. The live desk home is /pro/nfl/slate/today.
 * A 404 here made Overview "Weekly Slate" look broken.
 */
export default function NflWeeklySlateAliasPage() {
  redirect("/pro/nfl/slate/today");
}
