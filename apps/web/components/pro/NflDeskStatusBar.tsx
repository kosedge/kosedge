import Link from "next/link";
import { headers } from "next/headers";
import {
  fetchNflDataFreshness,
  isNflSeasonEngineDeskPath,
  shouldShowNflDataFreshnessBanner,
} from "@/lib/nfl-data-freshness";
import {
  fetchNflProductionReadiness,
  shouldShowNflPreseasonReadinessBanner,
} from "@/lib/nfl-production-readiness";
import { MODEL_TRANSPARENCY_HREF } from "@/lib/model-transparency-hub";

const DETAILS_HREF = `${MODEL_TRANSPARENCY_HREF}#desk-status`;

/**
 * One slim NFL desk status line — replaces the stacked readiness + freshness banners.
 * Probe logic unchanged; long policy copy lives on Model Transparency.
 * Parents mount this only on NFL Pro / Edge Board surfaces.
 */
export async function NflDeskStatusBar() {
  const pathname = (await headers()).get("x-pathname") || "";
  const skipFreshness = isNflSeasonEngineDeskPath(pathname);
  const [readiness, freshness] = await Promise.all([
    fetchNflProductionReadiness(),
    skipFreshness ? Promise.resolve(null) : fetchNflDataFreshness(),
  ]);

  const showReadiness = shouldShowNflPreseasonReadinessBanner(readiness);
  const showFreshness =
    freshness != null && shouldShowNflDataFreshnessBanner(freshness);

  if (!showReadiness && !showFreshness) {
    return null;
  }

  const tokens: string[] = [];
  if (showReadiness) tokens.push("PRESEASON");
  if (showFreshness) tokens.push("data stale");
  tokens.push("PLAY tags research-only");

  const tone = showFreshness
    ? {
        bar: "border-amber-500/40 bg-amber-500/10 text-amber-100",
        muted: "text-amber-100/70",
        link: "text-amber-100/55 hover:text-amber-50",
      }
    : {
        bar: "border-sky-500/35 bg-sky-500/10 text-sky-50",
        muted: "text-sky-50/70",
        link: "text-sky-50/55 hover:text-sky-50",
      };

  const expandLines: string[] = [];
  if (showFreshness && freshness?.blockers?.length) {
    expandLines.push(
      ...freshness.blockers.slice(0, 3).map((b) => `freshness: ${b}`),
    );
  } else if (showFreshness && freshness?.error) {
    expandLines.push(`freshness: ${freshness.error}`);
  }
  if (showReadiness && readiness.reasons?.length) {
    expandLines.push(
      ...readiness.reasons.slice(0, 3).map((r) => `readiness: ${r}`),
    );
  }

  return (
    <div
      role="status"
      data-testid="nfl-desk-status-bar"
      data-preseason-readiness={showReadiness ? "no-go" : undefined}
      className={`border-b ${tone.bar}`}
    >
      <div className="mx-auto flex max-w-6xl items-start gap-3 px-6 py-1.5 text-xs">
        <details className="min-w-0 flex-1">
          <summary className="cursor-pointer list-none font-medium tracking-tight marker:content-none [&::-webkit-details-marker]:hidden">
            <span className="truncate">{tokens.join(" · ")}</span>
          </summary>
          {expandLines.length > 0 ? (
            <p className={`mt-1.5 break-all ${tone.muted}`}>
              {expandLines.join(" · ")}
            </p>
          ) : (
            <p className={`mt-1.5 ${tone.muted}`}>
              Full policy and probe notes on Model Transparency.
            </p>
          )}
        </details>
        <Link
          href={DETAILS_HREF}
          className={`shrink-0 pt-px font-medium underline-offset-2 hover:underline ${tone.link}`}
        >
          Details
        </Link>
      </div>
    </div>
  );
}
