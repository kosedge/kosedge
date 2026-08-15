import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import CfbProjectGameClient from "@/components/pro/cfb/CfbProjectGameClient";
import { fetchCfbSeasonEngineStatus } from "@/lib/cfb-season-engine";
import {
  normalizeTeamCode,
  teamOptionsFromCodes,
} from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export default async function CfbProjectGamePage({
  searchParams,
}: {
  searchParams?:
    | Promise<Record<string, SearchValue>>
    | Record<string, SearchValue>;
}) {
  const sp =
    searchParams && typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<Record<string, SearchValue>>)
      : ((searchParams as Record<string, SearchValue>) ?? {});

  const status = await fetchCfbSeasonEngineStatus();
  const home = normalizeTeamCode(firstValue(sp.home) ?? "");
  const away = normalizeTeamCode(firstValue(sp.away) ?? "");
  const weekRaw = Number(firstValue(sp.week) ?? 1);
  const week = Number.isFinite(weekRaw) ? Math.max(0, Math.min(20, weekRaw)) : 1;
  const neutral =
    firstValue(sp.neutral) === "1" || firstValue(sp.neutral) === "true";
  const codes = [
    ...(status.team_codes ?? []),
    ...(home ? [home] : []),
    ...(away ? [away] : []),
  ];
  const teams = teamOptionsFromCodes(codes);
  const deepLinked = Boolean(home && away && home !== away);

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Project Game"
      summary="Research fair — projected score, favorite spread, total, win%, team totals, and σ. Not a wagering instruction. Markets may appear on Edge Board; this desk never blends them into KEI."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/slate"
      primaryLabel="Official slate"
      secondaryHref="/edge-board/cfb"
      secondaryLabel="Edge Board (markets)"
    >
      <div className="mt-2 mb-4 flex flex-wrap gap-3 text-xs">
        <Link
          href="/pro/cfb/model"
          className="min-h-11 inline-flex items-center font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
        >
          ← Model hub
        </Link>
        <Link
          href="/pro/cfb/slate"
          className="min-h-11 inline-flex items-center font-medium text-kos-text/65 hover:text-kos-text sm:min-h-0"
        >
          Slate →
        </Link>
      </div>

      {status.error ? (
        <p className="mb-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/65">
          Status probe failed ({status.error}). Team list may be incomplete —
          project-game still attempts Railway via BFF.
        </p>
      ) : null}

      <CfbProjectGameClient
        teams={teams}
        defaultHome={home || "TCU"}
        defaultAway={away || "UNC"}
        defaultWeek={deepLinked ? week : 0}
        defaultNeutral={neutral}
        autoRun={deepLinked}
        engineVersion={status.engine_version || undefined}
      />
    </SportHubShell>
  );
}
