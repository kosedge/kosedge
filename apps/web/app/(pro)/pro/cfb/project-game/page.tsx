import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import CfbProjectGameClient from "@/components/pro/cfb/CfbProjectGameClient";
import { fetchCfbSeasonEngineStatus } from "@/lib/cfb-season-engine";
import { teamOptionsFromCodes } from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

export default async function CfbProjectGamePage() {
  const status = await fetchCfbSeasonEngineStatus();
  const teams = teamOptionsFromCodes(status.team_codes);

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Project Game"
      summary="Market-style team projection — projected score, favorite spread, total, and win% with American moneyline, approximate QB / skill player hooks, plus scannable roster / unit / HFA / coaching drivers and early-season uncertainty."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/model"
      primaryLabel="Season Model hub"
      secondaryHref="/edge-board/cfb"
      secondaryLabel="Edge Board"
    >
      <div className="mt-2 mb-4 flex flex-wrap gap-3 text-xs">
        <Link
          href="/pro/cfb/model"
          className="min-h-11 inline-flex items-center font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
        >
          ← Season Model
        </Link>
        <Link
          href="/pro/cfb/tempo"
          className="min-h-11 inline-flex items-center font-medium text-kos-text/65 hover:text-kos-text sm:min-h-0"
        >
          Tempo →
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
        engineVersion={status.engine_version || undefined}
      />
    </SportHubShell>
  );
}
