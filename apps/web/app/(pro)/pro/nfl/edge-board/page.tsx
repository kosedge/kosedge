import { redirect } from "next/navigation";

/** Legacy / mistaken path — Edge Board lives under /edge-board/nfl. */
export default function NflEdgeBoardAliasPage() {
  redirect("/edge-board/nfl");
}
