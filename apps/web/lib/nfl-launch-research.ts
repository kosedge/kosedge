import "server-only";
import { loadNflWebLaunchPointer } from "@/lib/nfl-preseason-artifacts";

/** Guest-facing one-liner for season desks (survivor / game boxes / model). */
export function nflLaunchResearchDeskNotice(): string | null {
  const pointer = loadNflWebLaunchPointer();
  if (!pointer?.bundle_id) return null;
  const n =
    typeof pointer.n_team_sims === "number"
      ? pointer.n_team_sims.toLocaleString()
      : null;
  const eng = pointer.engine_version || "season engine";
  const when = pointer.generated_at_utc?.slice(0, 10);
  return [
    "Launch-current research",
    n ? `${n} team W/L paths` : null,
    eng,
    when ? `generated ${when}` : null,
    "Interactive desks default to research depth (≥2k); thin runs labeled low-depth estimate",
  ]
    .filter(Boolean)
    .join(" · ");
}
