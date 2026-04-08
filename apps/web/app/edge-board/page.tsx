// apps/web/app/edge-board/page.tsx
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default function EdgeBoardPage() {
  redirect("/edge-board/ncaam");
}
