import { jsonOk } from "@/lib/api/response";

export const dynamic = "force-dynamic";

export async function GET() {
  return jsonOk({ ok: true, ts: Date.now() });
}
