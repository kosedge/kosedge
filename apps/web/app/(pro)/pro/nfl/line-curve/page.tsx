import LineCurveResearchPanel from "@/components/pro/line-curve/LineCurveResearchPanel";
import SportHubShell from "@/components/pro/SportHubShell";

export const dynamic = "force-dynamic";

export default function NflLineCurvePage() {
  return (
    <SportHubShell
      sportKey="nfl"
      sportName="NFL"
      base="/pro/nfl"
      title="Line Curve"
      badge="Research"
      summary="Alternate spreads as a pricing surface against the model margin distribution. Not a teaser calculator. Research labels only."
      truthStates={["MODEL"]}
      truthTestId="nfl-line-curve-truth"
      honestyNote="Phase 1 Line Curve is research-only — numbers only, no PLAY language, no production publish."
      primaryHref="/pro/nfl/fair-lines"
      primaryLabel="KEI Lines"
      secondaryHref="/pro/nfl/edges"
      secondaryLabel="Edges desk"
    >
      <LineCurveResearchPanel sport="nfl" />
    </SportHubShell>
  );
}
