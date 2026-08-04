"use client";

import { useEffect, useState } from "react";
import SeasonEngineSurvivorClient from "@/components/pro/nfl/SeasonEngineSurvivorClient";
import SeasonEngineSurvivorPlannerClient from "@/components/pro/nfl/SeasonEngineSurvivorPlannerClient";

type Mode = "planner" | "helper";

export default function SeasonEngineSurvivorShell({
  defaultWeek = 1,
  engineVersion,
  depthSource,
  depthAsOf,
  defaultMode = "planner",
}: {
  defaultWeek?: number;
  engineVersion?: string;
  depthSource?: string;
  depthAsOf?: string;
  defaultMode?: Mode;
}) {
  const [mode, setMode] = useState<Mode>(defaultMode);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const q = new URLSearchParams(window.location.search).get("mode");
    if (q === "helper" || q === "planner") setMode(q);
  }, []);

  function selectMode(next: Mode) {
    setMode(next);
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    params.set("mode", next);
    const qs = params.toString();
    window.history.replaceState(
      null,
      "",
      qs ? `${window.location.pathname}?${qs}` : window.location.pathname,
    );
  }

  return (
    <div className="space-y-5">
      <div
        className="inline-flex rounded-xl border border-white/10 bg-black/30 p-1"
        role="tablist"
        aria-label="Survivor mode"
      >
        <button
          type="button"
          role="tab"
          aria-selected={mode === "planner"}
          onClick={() => selectMode("planner")}
          className={`min-h-10 rounded-lg px-3.5 text-sm font-semibold transition ${
            mode === "planner"
              ? "bg-kos-gold/20 text-kos-gold"
              : "text-kos-text/65 hover:text-kos-text"
          }`}
        >
          17-week planner
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "helper"}
          onClick={() => selectMode("helper")}
          className={`min-h-10 rounded-lg px-3.5 text-sm font-semibold transition ${
            mode === "helper"
              ? "bg-kos-gold/20 text-kos-gold"
              : "text-kos-text/65 hover:text-kos-text"
          }`}
        >
          Single-week helper
        </button>
      </div>

      {mode === "planner" ? (
        <SeasonEngineSurvivorPlannerClient
          engineVersion={engineVersion}
          depthSource={depthSource}
          depthAsOf={depthAsOf}
        />
      ) : (
        <SeasonEngineSurvivorClient
          defaultWeek={defaultWeek}
          engineVersion={engineVersion}
          depthSource={depthSource}
          depthAsOf={depthAsOf}
        />
      )}
    </div>
  );
}
