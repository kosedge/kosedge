import { redirect } from "next/navigation";

/** Alias for users who type /pro/nfl/boards. */
export default function NflBoardsAliasPage() {
  redirect("/edge-board/nfl");
}
