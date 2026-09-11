import LineCurveResearchPanel from "@/components/pro/line-curve/LineCurveResearchPanel";
import SportHubShell from "@/components/pro/SportHubShell";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

export default function CfbLineCurvePage() {
  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Line Curve"
      badge="Research"
      summary="Alternate spreads as a pricing surface against the model margin distribution. Not a teaser calculator. Research labels only."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-line-curve-truth"
      honestyNote={`${cfbModelDeskHonestyNote()} Phase 1 Line Curve is research-only — no publish, no stake tags.`}
      primaryHref="/pro/cfb/project-game"
      primaryLabel="Project Game"
      secondaryHref="/pro/cfb/fair-lines"
      secondaryLabel="KEI Lines"
    >
      <LineCurveResearchPanel sport="cfb" />
    </SportHubShell>
  );
}
