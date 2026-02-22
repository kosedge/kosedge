import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";
import { getCurrentSectionNumber } from "@/lib/insights/rotation";
import { getSection, getAllPillarMetas } from "@/lib/insights/pillars";
import type { InsightBlock } from "@/lib/insights/types";

function SectionBody({ blocks }: { blocks: InsightBlock[] }) {
  return (
    <div className="mt-4 space-y-4">
      {blocks.map((block, i) =>
        typeof block === "string" ? (
          <p key={i} className="leading-7 text-kos-text/90">
            {block}
          </p>
        ) : (
          <ul
            key={i}
            className="list-disc list-inside space-y-1 text-kos-text/90"
          >
            {block.map((item, j) => (
              <li key={j}>{item}</li>
            ))}
          </ul>
        ),
      )}
    </div>
  );
}

function getWeekLabel(sectionNum: number): string {
  const labels = [
    "1.1, 2.1, 3.1 …",
    "1.2, 2.2, 3.2 …",
    "1.3, 2.3, 3.3 …",
    "1.4, 2.4, 3.4 …",
  ];
  return labels[sectionNum - 1] ?? "";
}

export default function InsightsPage() {
  const sectionNum = getCurrentSectionNumber();
  const pillarMetas = getAllPillarMetas();
  const weekLabel = getWeekLabel(sectionNum);

  return (
    <main className="min-h-screen bg-kos-black">
      <SiteHeader />
      <div className="mx-auto max-w-4xl px-6 py-14">
        <h1 className="text-4xl font-semibold tracking-tight text-kos-text">
          Insights
        </h1>
        <p className="mt-3 text-kos-text/80">
          Premium-grade sports analytics. New section set every Monday.
        </p>
        <p className="mt-1 text-sm text-kos-text/60">This week: {weekLabel}</p>

        <div className="mt-10 space-y-2">
          {pillarMetas.map((meta) => {
            const section = getSection(meta.number, sectionNum);
            if (!section) return null;

            const isPro = meta.isPro;

            return (
              <details
                key={meta.number}
                className="group rounded-xl border border-kos-border bg-kos-surface/40"
              >
                <summary className="cursor-pointer list-none px-6 py-4 text-xl font-semibold text-kos-gold hover:opacity-90 transition-opacity [&::-webkit-details-marker]:hidden">
                  {section.title}
                </summary>
                <div className="relative border-t border-kos-border px-6 pb-6 pt-4">
                  <div
                    className={
                      isPro ? "select-none blur-md pointer-events-none" : ""
                    }
                  >
                    <SectionBody blocks={section.body} />
                  </div>
                  {isPro && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center rounded-b-xl bg-kos-black/60 pt-4">
                      <p className="text-center text-kos-text/90 font-medium">
                        Pillars 5–7 are for Pro members
                      </p>
                      <Link
                        href="/pro"
                        className="mt-4 inline-flex rounded-xl bg-kos-gold px-5 py-3 text-black font-semibold shadow hover:opacity-90"
                      >
                        Go Pro
                      </Link>
                    </div>
                  )}
                </div>
              </details>
            );
          })}
        </div>
      </div>
    </main>
  );
}
