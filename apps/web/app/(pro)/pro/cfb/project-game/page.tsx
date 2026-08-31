import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import CfbProjectGameClient from "@/components/pro/cfb/CfbProjectGameClient";
import { fetchCfbSeasonEngineStatus } from "@/lib/cfb-season-engine";
import {
  normalizeTeamCode,
  teamOptionsFromCodes,
} from "@/lib/cfb-season-engine-format";
import {
  matchupLabel,
  officialSlateWeekForMatchup,
  packagedOfficialWeekBoard,
} from "@/lib/cfb-official-slate";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";
export const maxDuration = 20;

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
  const defaultHome = home || "TCU";
  const defaultAway = away || "UNC";
  const weekParam = firstValue(sp.week);
  const weekFromQuery =
    weekParam != null && String(weekParam).trim() !== ""
      ? Number(weekParam)
      : NaN;
  // Bare /pro/cfb/project-game defaults UNC@TCU — that matchup is Week 0 on the
  // official slate. Never invent Week 1 when the slate already knows the week.
  const weekFromSlate =
    officialSlateWeekForMatchup(defaultHome, defaultAway) ??
    officialSlateWeekForMatchup(home, away);
  const week = Number.isFinite(weekFromQuery)
    ? Math.max(0, Math.min(20, weekFromQuery))
    : (weekFromSlate ?? 0);
  const neutral =
    firstValue(sp.neutral) === "1" || firstValue(sp.neutral) === "true";
  const codes = [
    ...(status.team_codes ?? []),
    ...(home ? [home] : []),
    ...(away ? [away] : []),
    "TCU",
    "UNC",
    "USC",
    "UGA",
    "OSU",
  ];
  const teams = teamOptionsFromCodes(codes);
  const slateRows = (packagedOfficialWeekBoard().games ?? []).map((g) => ({
    key: g.game_id || `${g.away}@${g.home}-${g.week}`,
    label: `W${g.week}${g.status === "final" ? " final" : ""} · ${g.away} @ ${g.home}${
      g.away_score != null && g.home_score != null
        ? ` (${g.away_score}–${g.home_score})`
        : ""
    }`,
    home: g.home.replace(/^fcs:/i, ""),
    away: g.away.replace(/^fcs:/i, ""),
    week: g.week,
    neutral: Boolean(g.neutral_site),
    title: matchupLabel(g),
  }));

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Project Game"
      summary="Model is research-fair. When the matchup is on the W0/W1 slate, KEI is the published line. Edge / Tag lives on the Edge Board."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/slate?week=1"
      primaryLabel="Official slate"
      secondaryHref="/edge-board/cfb?week=1"
      secondaryLabel="Edge Board"
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
        <p className="mb-4 rounded-lg border border-amber-400/25 bg-amber-400/8 px-3 py-2 text-xs text-kos-text/70">
          Model unreachable ({status.error}). Form still runs through the BFF —
          if Railway is down you will see an honest project-game error, not a
          black frame.
        </p>
      ) : null}

      <CfbProjectGameClient
        teams={teams}
        defaultHome={defaultHome}
        defaultAway={defaultAway}
        defaultWeek={week}
        defaultNeutral={neutral}
        engineVersion={status.engine_version || undefined}
        slateRows={slateRows}
      />
    </SportHubShell>
  );
}
