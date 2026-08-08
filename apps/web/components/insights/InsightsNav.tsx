import Link from "next/link";
import type { InsightsTab } from "@/lib/insights/types";

const TABS: Array<{ id: InsightsTab; label: string; href: string }> = [
  { id: "this-week", label: "This Week", href: "/insights" },
  { id: "doctrine", label: "Doctrine", href: "/insights/doctrine" },
  { id: "sports", label: "Sports", href: "/insights/sports" },
];

export default function InsightsNav({ active }: { active: InsightsTab }) {
  return (
    <nav
      aria-label="Insights sections"
      className="mt-8 flex gap-1 overflow-x-auto border-b border-kos-border pb-px"
    >
      {TABS.map((tab) => {
        const isActive = tab.id === active;
        return (
          <Link
            key={tab.id}
            href={tab.href}
            className={
              isActive
                ? "shrink-0 border-b-2 border-kos-gold px-4 py-2.5 text-sm font-semibold text-kos-gold"
                : "shrink-0 border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-kos-text/60 hover:text-kos-text"
            }
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
