"use client";

import { useEffect, useState } from "react";
import LineCurveChart from "@/components/pro/line-curve/LineCurveChart";
import type {
  LineCurveResult,
  TwoLegOptimizeResult,
} from "@/lib/line-curve/types";

function fmtLine(n: number): string {
  return n > 0 ? `+${n}` : String(n);
}

function fmtPct(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmtEv(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(3)}`;
}

function fmtAm(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n > 0 ? `+${Math.round(n)}` : String(Math.round(n));
}

function labelClass(label: string): string {
  if (label === "BEST VALUE") return "text-green-300";
  if (label === "OVERPRICED") return "text-rose-300";
  if (label === "INSUFFICIENT") return "text-amber-300";
  return "text-kos-text/70";
}

export default function LineCurveResearchPanel({
  sport,
}: {
  sport: "cfb" | "nfl";
}) {
  const [mode, setMode] = useState<"one" | "two">("one");
  const [side, setSide] = useState<"Missouri" | "Oklahoma">("Missouri");
  const [curve, setCurve] = useState<LineCurveResult | null>(null);
  const [joint, setJoint] = useState<TwoLegOptimizeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    async function load() {
      try {
        if (mode === "one") {
          const res = await fetch(
            `/api/line-curve?fixture=missouri-oklahoma&side=${encodeURIComponent(side)}`,
            { cache: "no-store" },
          );
          const json = (await res.json()) as {
            curve?: LineCurveResult;
            error?: string;
          };
          if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
          if (!cancelled) {
            setCurve(json.curve ?? null);
            setJoint(null);
          }
        } else {
          const res = await fetch("/api/line-curve/optimize", {
            method: "POST",
            headers: { "content-type": "application/json" },
            cache: "no-store",
            body: JSON.stringify({ fixture: "missouri-oklahoma" }),
          });
          const json = (await res.json()) as {
            result?: TwoLegOptimizeResult;
            error?: string;
          };
          if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
          if (!cancelled) {
            setJoint(json.result ?? null);
            setCurve(null);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Line Curve request failed",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [mode, side, sport]);

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setMode("one")}
            className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
              mode === "one"
                ? "border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                : "border-white/10 bg-white/5 text-kos-text/70"
            }`}
          >
            Single game
          </button>
          <button
            type="button"
            onClick={() => setMode("two")}
            className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
              mode === "two"
                ? "border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                : "border-white/10 bg-white/5 text-kos-text/70"
            }`}
          >
            2-leg optimizer
          </button>
          {mode === "one" ? (
            <>
              <button
                type="button"
                onClick={() => setSide("Missouri")}
                className={`rounded-full border px-3 py-1.5 text-xs ${
                  side === "Missouri"
                    ? "border-white/25 bg-white/10"
                    : "border-white/10 bg-black/40"
                }`}
              >
                Missouri
              </button>
              <button
                type="button"
                onClick={() => setSide("Oklahoma")}
                className={`rounded-full border px-3 py-1.5 text-xs ${
                  side === "Oklahoma"
                    ? "border-white/25 bg-white/10"
                    : "border-white/10 bg-black/40"
                }`}
              >
                Oklahoma
              </button>
            </>
          ) : null}
        </div>
        <p className="mt-3 text-xs leading-relaxed text-kos-text/55">
          Research fixture: Missouri +1.5 / Oklahoma +1.5 combined −103. Numbers
          only — no stake recommendation. Posted sportsbook prices only; missing
          alts are not interpolated. {sport.toUpperCase()} Phase 1 is spreads.
        </p>
      </section>

      {error ? (
        <p className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          {error}
        </p>
      ) : null}
      {loading ? (
        <p className="text-sm text-kos-text/55">Loading Line Curve…</p>
      ) : null}

      {curve && !curve.ok ? (
        <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-kos-text/70">
          INSUFFICIENT — {curve.message}
        </p>
      ) : null}

      {curve?.ok ? (
        <>
          <section className="grid gap-3 sm:grid-cols-3">
            <Chip label="Base market" value={fmtLine(curve.baseLine)} />
            <Chip
              label="Model fair line"
              value={fmtLine(Number(curve.modelFairLine.toFixed(1)))}
            />
            <Chip label="Book" value={curve.book} />
          </section>
          <section className="rounded-2xl border border-white/10 bg-black/30 p-4">
            <h2 className="mb-3 text-sm font-semibold text-kos-text">
              Cover vs implied
            </h2>
            <LineCurveChart points={curve.points} />
          </section>
          <section className="overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
            <table className="min-w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wide text-kos-text/45">
                <tr>
                  <th className="px-3 py-2">Alt</th>
                  <th className="px-3 py-2">Book</th>
                  <th className="px-3 py-2">Implied</th>
                  <th className="px-3 py-2">Model cover</th>
                  <th className="px-3 py-2">Push</th>
                  <th className="px-3 py-2">Fair</th>
                  <th className="px-3 py-2">EV /$</th>
                  <th className="px-3 py-2">Marginal</th>
                  <th className="px-3 py-2">Label</th>
                </tr>
              </thead>
              <tbody>
                {curve.points.map((p) => (
                  <tr key={p.altLine} className="border-t border-white/8">
                    <td className="px-3 py-2 font-medium">
                      {fmtLine(p.altLine)}
                    </td>
                    <td className="px-3 py-2">{fmtAm(p.americanOdds)}</td>
                    <td className="px-3 py-2">
                      {fmtPct(p.impliedProbability)}
                    </td>
                    <td className="px-3 py-2">
                      {fmtPct(p.modelCoverProbability)}
                    </td>
                    <td className="px-3 py-2">
                      {fmtPct(p.modelPushProbability)}
                    </td>
                    <td className="px-3 py-2">{fmtAm(p.fairAmericanOdds)}</td>
                    <td className="px-3 py-2">{fmtEv(p.evPerDollar)}</td>
                    <td className="px-3 py-2">
                      {p.marginalCostPerProbPoint == null
                        ? "—"
                        : p.marginalCostPerProbPoint.toFixed(2)}
                    </td>
                    <td
                      className={`px-3 py-2 font-semibold ${labelClass(p.label)}`}
                    >
                      {p.label}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <p className="text-[11px] text-kos-text/40">
            Provenance {curve.oddsSnapshotId} · {curve.modelRunId} ·{" "}
            {curve.timestamp}
          </p>
        </>
      ) : null}

      {joint && !joint.ok ? (
        <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-kos-text/70">
          INSUFFICIENT — {joint.message}
        </p>
      ) : null}

      {joint?.ok ? (
        <>
          <p className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-xs leading-relaxed text-kos-text/60">
            {joint.correlation.note}
          </p>
          <section className="overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
            <table className="min-w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wide text-kos-text/45">
                <tr>
                  <th className="px-3 py-2">Rank</th>
                  <th className="px-3 py-2">Leg A</th>
                  <th className="px-3 py-2">Leg B</th>
                  <th className="px-3 py-2">Book parlay</th>
                  <th className="px-3 py-2">Joint cover</th>
                  <th className="px-3 py-2">Fair</th>
                  <th className="px-3 py-2">EV /$</th>
                  <th className="px-3 py-2">Label</th>
                </tr>
              </thead>
              <tbody>
                {joint.combos.slice(0, 16).map((c) => (
                  <tr
                    key={`${c.lineA}-${c.lineB}`}
                    className="border-t border-white/8"
                  >
                    <td className="px-3 py-2">{c.rank}</td>
                    <td className="px-3 py-2">{fmtLine(c.lineA)}</td>
                    <td className="px-3 py-2">{fmtLine(c.lineB)}</td>
                    <td className="px-3 py-2">
                      {fmtAm(c.bookParlayAmerican)}
                      <span className="ml-1 text-kos-text/35">
                        {c.parlayPriceSource === "book_quoted"
                          ? "quoted"
                          : "from legs"}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {fmtPct(c.modelJointCoverProbability)}
                    </td>
                    <td className="px-3 py-2">{fmtAm(c.fairAmericanOdds)}</td>
                    <td className="px-3 py-2">{fmtEv(c.evPerDollar)}</td>
                    <td
                      className={`px-3 py-2 font-semibold ${labelClass(c.label)}`}
                    >
                      {c.label}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : null}
    </div>
  );
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/35 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-kos-text/45">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-semibold text-kos-text">{value}</p>
    </div>
  );
}
