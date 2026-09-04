import SportProHeader from "@/components/pro/SportProHeader";
import EdgeBoardSportClient from "@/components/EdgeBoardSportClient";
import { normalizeNflEdgeBoardSlate } from "@/lib/build-edge-board-rows";
import {
  edgeBoardAssembleBootstrapScript,
  edgeBoardAssembleHref,
} from "@/lib/edge-board-assemble-href";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";

export const dynamic = "force-dynamic";

/**
 * Edge Board — SSR shell only.
 * Board rows client-fetch /api/edge-board/[sport]/assemble so HTML is not
 * held open on model-service (Alex: SSR wait waterfall, not download).
 * #12 GO-1: inline bootstrap starts assemble during HTML parse (before hydrate).
 * Do not await assemble here — honesty stays Loading / as-of unavailable.
 */
export default async function EdgeBoardSportPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport?: string }> | { sport?: string };
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  // Parallelize params + searchParams — do not block shell on model-service.
  const paramsPromise =
    params && typeof (params as Promise<unknown>).then === "function"
      ? (params as Promise<{ sport?: string }>)
      : Promise.resolve((params as { sport?: string }) ?? {});
  const searchPromise =
    searchParams &&
    typeof (searchParams as Promise<unknown>).then === "function"
      ? (searchParams as Promise<Record<string, string | string[] | undefined>>)
      : Promise.resolve(
          (searchParams as Record<string, string | string[] | undefined>) ?? {},
        );

  const [resolved, sp] = await Promise.all([paramsPromise, searchPromise]);
  const sportKey = resolveSportKey(resolved?.sport, "ncaam");
  const sportName = sportDisplayLabel(sportKey);
  const slateRaw = Array.isArray(sp.slate) ? sp.slate[0] : sp.slate;
  const slate =
    sportKey === "nfl" ? normalizeNflEdgeBoardSlate(slateRaw) : "week1";
  const cfbWeekRaw = Array.isArray(sp.week) ? sp.week[0] : sp.week;
  const cfbWeek: 0 | 1 = sportKey === "cfb" ? (cfbWeekRaw === "0" ? 0 : 1) : 1;
  const assembleHref = edgeBoardAssembleHref({ sportKey, slate, cfbWeek });

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      {/* #12 GO-1: start assemble with HTML — do not await (Alex waterfall). */}
      <link
        rel="preload"
        as="fetch"
        href={assembleHref}
        crossOrigin="use-credentials"
      />
      <script
        dangerouslySetInnerHTML={{
          __html: edgeBoardAssembleBootstrapScript(assembleHref),
        }}
      />
      <SportProHeader activeSport={sportKey} />
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-edge-green/12 blur-3xl animate-pulse-slow" />
        <div className="absolute top-24 -left-40 h-[520px] w-[520px] rounded-full bg-edge-green/10 blur-3xl animate-pulse-slow" />
        <div className="absolute -bottom-56 -right-56 h-[640px] w-[640px] rounded-full bg-kos-gold/8 blur-3xl animate-pulse-slow" />
        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(57,255,20,0.16) 1px, transparent 1px), linear-gradient(to bottom, rgba(57,255,20,0.08) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
        <div className="absolute inset-0 bg-linear-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <main className="relative z-10 w-full px-5 sm:px-6 pt-6 pb-16 sm:pt-8">
        <EdgeBoardSportClient
          sportKey={sportKey}
          sportName={sportName}
          slate={slate}
          cfbWeek={cfbWeek}
        />
      </main>
    </div>
  );
}
