"use client";

import { useEffect, useState } from "react";
import LineCurveChart from "@/components/pro/line-curve/LineCurveChart";
import {
  INDEPENDENT_JOINT_CAPTION,
  INDEPENDENT_JOINT_HEADING,
  impliesCorrelationAdjusted,
  jointCoverColumnLabel,
  jointProbabilityCaption,
} from "@/lib/line-curve/joint-presentation";
import { independentJointModel } from "@/lib/line-curve/joint-optimizer";
import { correlationMeta } from "@/lib/line-curve/joint-optimizer";
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

const phase1Independence = correlationMeta(independentJointModel());

export default function LineCurveResearchPanel({
  sport,
}: {
  sport: "cfb" | "nfl";
}) {
  const [mode, setMode] = useState<"one" | "two">("one");
  const [curve, setCurve] = useState<LineCurveResult | null>(null);
  const [joint, setJoint] = useState<TwoLegOptimizeResult | null>(null);
  const [independenceCaption, setIndependenceCaption] = useState(
    jointProbabilityCaption(phase1Independence),
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    async function load() {
      try {
        if (mode === "one") {
          const res = await fetch(`/api/line-curve?sport=${sport}`, {
            cache: "no-store",
          });
          const json = (await res.json()) as {
            curve?: LineCurveResult;
            error?: string;
          };
          if (!res.ok && res.status !== 200) {
            throw new Error(json.error || `HTTP ${res.status}`);
          }
          if (!cancelled) {
            setCurve(json.curve ?? null);
            setJoint(null);
          }
        } else {
          const res = await fetch("/api/line-curve/optimize", {
            method: "POST",
            headers: { "content-type": "application/json" },
            cache: "no-store",
            body: JSON.stringify({}),
          });
          const json = (await res.json()) as {
            result?: TwoLegOptimizeResult;
            independenceCaption?: string;
            error?: string;
          };
          if (!res.ok && res.status !== 200) {
            throw new Error(json.error || `HTTP ${res.status}`);
          }
          if (!cancelled) {
            setJoint(json.result ?? null);
            setCurve(null);
            if (json.independenceCaption) {
              setIndependenceCaption(json.independenceCaption);
            }
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
  }, [mode, sport]);

  const jointMeta = joint?.ok ? joint.correlation : phase1Independence;
  const correlationAdjusted = impliesCorrelationAdjusted(jointMeta);

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
        </div>
        <p className="mt-3 text-xs leading-relaxed text-kos-text/55">
          The book lets you move the number anywhere. Line Curve asks what each
          half-point is worth on the model margin distribution, and what they
          are charging for it. Posted alt prices only — no interpolation, no
          teaser table, no stake recommendation. {sport.toUpperCase()} Phase 1
          is spreads.
        </p>
      </section>

      {mode === "two" ? (
        <section
          data-testid="line-curve-independence"
          className="rounded-2xl border border-amber-400/25 bg-amber-400/8 px-4 py-3 text-xs leading-relaxed text-kos-text/75"
        >
          <p className="font-semibold text-amber-100">
            {correlationAdjusted
              ? "Correlation-adjusted joint"
              : INDEPENDENT_JOINT_HEADING}
          </p>
          <p className="mt-1">
            {correlationAdjusted
              ? independenceCaption
              : INDEPENDENT_JOINT_CAPTION}
          </p>
          {!correlationAdjusted ? (
            <p className="mt-1 text-kos-text/50">
              Same-game combinations are refused. BEST VALUE is never assigned
              from naive independence on one game.
            </p>
          ) : null}
        </section>
      ) : null}

      {error ? (
        <p className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          {error}
        </p>
      ) : null}
      {loading ? (
        <p className="text-sm text-kos-text/55">Loading Line Curve…</p>
      ) : null}

      {curve && !curve.ok ? (
        <p
          data-testid="line-curve-insufficient"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-kos-text/70"
        >
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
        <p
          data-testid="line-curve-insufficient"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-kos-text/70"
        >
          INSUFFICIENT — {joint.message}
        </p>
      ) : null}

      {joint?.ok ? (
        <section className="overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="min-w-full text-left text-xs">
            <thead className="text-[11px] uppercase tracking-wide text-kos-text/45">
              <tr>
                <th className="px-3 py-2">Rank</th>
                <th className="px-3 py-2">Leg A</th>
                <th className="px-3 py-2">Leg B</th>
                <th className="px-3 py-2">Book parlay</th>
                <th className="px-3 py-2">
                  {jointCoverColumnLabel(jointMeta)}
                </th>
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
                    {!impliesCorrelationAdjusted(c.correlation) ? (
                      <span className="ml-1 text-kos-text/35">indep.</span>
                    ) : null}
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
