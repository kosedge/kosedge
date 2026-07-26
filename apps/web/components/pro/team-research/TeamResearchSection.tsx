import type { ReactNode } from "react";
import type { TeamResearchSectionConfig } from "@/lib/team-research";

export default function TeamResearchSection({
  config,
  children,
}: {
  config: TeamResearchSectionConfig;
  children?: ReactNode;
}) {
  const isLive = config.status === "live";

  return (
    <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-kos-text">
            {config.title}
          </h3>
          <p className="mt-1 text-sm text-kos-text/70">{config.description}</p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
            isLive
              ? "border-emerald-400/35 bg-emerald-400/10 text-emerald-200"
              : "border-amber-400/35 bg-amber-400/10 text-amber-100"
          }`}
        >
          {isLive ? "Live" : "Data pending"}
        </span>
      </div>

      <div className="mt-4">
        {children ? (
          children
        ) : (
          <p className="rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-kos-text/70">
            {config.emptyCopy}
          </p>
        )}
      </div>
    </section>
  );
}
