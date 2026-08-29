import "server-only";

import { env } from "@/lib/env";

export type NflProductionReadiness = {
  status: "go" | "no-go" | "unknown";
  reasons: string[];
  sampleSize: number | null;
  clvOk: boolean | null;
  error?: string;
};

export async function fetchNflProductionReadiness(): Promise<NflProductionReadiness> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return {
      status: "unknown",
      reasons: [],
      sampleSize: null,
      clvOk: null,
      error: "MODEL_SERVICE_URL unset",
    };
  }
  try {
    const res = await fetch(
      `${base.replace(/\/+$/, "")}/health/nfl-production-readiness`,
      { next: { revalidate: 60 } },
    );
    const raw = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    // FastAPI may wrap in detail when raising 503, or return flat body.
    const body =
      raw && typeof raw === "object" && raw.detail && typeof raw.detail === "object"
        ? (raw.detail as Record<string, unknown>)
        : raw;
    if (!res.ok && !body.status) {
      return {
        status: "unknown",
        reasons: [],
        sampleSize: null,
        clvOk: null,
        error: `http_${res.status}`,
      };
    }
    const checks =
      body.gating_checks && typeof body.gating_checks === "object"
        ? (body.gating_checks as Record<string, unknown>)
        : body.checks && typeof body.checks === "object"
          ? (body.checks as Record<string, unknown>)
          : {};
    const metrics =
      body.metrics && typeof body.metrics === "object"
        ? (body.metrics as Record<string, unknown>)
        : {};
    const statusRaw = String(body.status || "unknown").toLowerCase();
    const status =
      statusRaw === "go" || statusRaw === "no-go"
        ? (statusRaw as "go" | "no-go")
        : "unknown";
    const reasons = Array.isArray(body.reasons)
      ? body.reasons.map((r) => String(r))
      : [];
    const sampleSize =
      typeof metrics.sample_size === "number"
        ? metrics.sample_size
        : typeof body.sample_size === "number"
          ? body.sample_size
          : null;
    const clvOk =
      typeof checks.clv_ok === "boolean" ? checks.clv_ok : null;
    return { status, reasons, sampleSize, clvOk };
  } catch (err) {
    return {
      status: "unknown",
      reasons: [],
      sampleSize: null,
      clvOk: null,
      error: err instanceof Error ? err.message : "fetch_failed",
    };
  }
}

export function shouldShowNflPreseasonReadinessBanner(
  readiness: NflProductionReadiness,
): boolean {
  if (readiness.status !== "no-go") return false;
  // Preseason signature: empty holdout / sample 0.
  if (readiness.sampleSize === 0) return true;
  if (readiness.reasons.includes("sample_size_ok")) return true;
  if (readiness.reasons.includes("low_sample_size")) return true;
  return false;
}

/** Invariant 6: readiness no-go ⇒ no PLAY stake tags. */
export function readinessBlocksPlay(
  readiness: NflProductionReadiness,
): boolean {
  return readiness.status === "no-go";
}
