import CfbOfficialSlatePanel from "@/components/pro/cfb/CfbOfficialSlatePanel";
import SportHubShell from "@/components/pro/SportHubShell";
import {
  officialSlateAttribution,
  officialSlateHrefForWeek,
  parseOfficialSlateWeek,
} from "@/lib/cfb-official-slate";
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

export default async function CfbOfficialSlatePage({
  searchParams,
}: {
  searchParams?:
    | Promise<Record<string, SearchValue>>
    | Record<string, SearchValue>;
}) {
  const sp =
    searchParams &&
    typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<Record<string, SearchValue>>)
      : ((searchParams as Record<string, SearchValue>) ?? {});
  const week = parseOfficialSlateWeek(firstValue(sp.week));

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Official slate"
      summary={officialSlateAttribution()}
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={`${cfbModelDeskHonestyNote()} Slate identity is the KosEdge artifact (used_in_spread=false).`}
      primaryHref="/pro/cfb/project-game"
      primaryLabel="Project Game"
      secondaryHref="/edge-board/cfb?week=1"
      secondaryLabel="Edge Board (markets)"
    >
      <CfbOfficialSlatePanel
        week={week}
        hrefForWeek={officialSlateHrefForWeek}
      />
    </SportHubShell>
  );
}
