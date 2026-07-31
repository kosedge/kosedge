import { redirect } from "next/navigation";

/** Bare /pro/nfl/slate has no [date] segment — land on the writer slate. */
export default function NflSlateIndexPage() {
  redirect("/pro/nfl/slate/today");
}
