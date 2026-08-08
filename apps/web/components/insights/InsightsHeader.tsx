import type { InsightsTab } from "@/lib/insights/types";
import InsightsNav from "./InsightsNav";

const COPY: Record<
  InsightsTab,
  { eyebrow: string; title: string; blurb: string }
> = {
  "this-week": {
    eyebrow: "Desk notes",
    title: "This Week",
    blurb:
      "Short, dated thinking from the KosEdge desk — market vs model, reprice logic, survivor traps, and process notes. Free gets a few open notes; Pro gets the full set.",
  },
  doctrine: {
    eyebrow: "House rules",
    title: "Doctrine",
    blurb:
      "Evergreen process pillars. How KosEdge thinks — free by design. No module numbers. Trust the desk before you pay for the diary.",
  },
  sports: {
    eyebrow: "Filter",
    title: "By Sport",
    blurb:
      "Desk notes and doctrine tagged to sports that have content. Empty sports stay off the list.",
  },
};

export default function InsightsHeader({ active }: { active: InsightsTab }) {
  const copy = COPY[active];

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-kos-gold/80">
        Insights · {copy.eyebrow}
      </p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight text-kos-text">
        {copy.title}
      </h1>
      <p className="mt-3 max-w-2xl text-kos-text/75 leading-7">{copy.blurb}</p>
      <InsightsNav active={active} />
    </div>
  );
}
