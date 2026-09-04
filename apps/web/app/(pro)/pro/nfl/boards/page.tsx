import { permanentRedirect } from "next/navigation";

/** Alias for users who type /pro/nfl/boards — canonical is /edge-board/nfl. */
export default function NflBoardsAliasPage() {
  permanentRedirect("/edge-board/nfl");
}
