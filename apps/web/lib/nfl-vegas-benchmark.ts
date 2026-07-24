import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export type NflVegasBenchmarkReport = {
  generatedAt: string;
  modelVersion: string;
  methodology: {
    summary: string;
    trainSeasons: string;
    tuneSeasons: string;
    testSeasons: string;
    testSampleSize: number;
    significanceTest: string;
    sourceScripts: string[];
    caveats: string[];
  };
  results2025Holdout: {
    spreadMae: { model: number; vegas: number };
    totalMae: { model: number; vegas: number };
    winProbabilityBrier: { model: number; vegas: number };
    spreadSignificance: {
      diff: number;
      ci95Low: number;
      ci95High: number;
      significant: boolean;
    };
  };
  resultsFull13YrSample: {
    seasons: string;
    sampleSize: number;
    note: string;
    spreadMae: { model: number; vegas: number };
    totalMae: { model: number; vegas: number };
  };
};

function findRepoRoot(): string | null {
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    const dataOps = path.join(current, "data", "ops");
    if (existsSync(dataOps)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

export function loadNflVegasBenchmarkReport(): NflVegasBenchmarkReport | null {
  try {
    const repoRoot = findRepoRoot();
    if (!repoRoot) return null;
    const reportPath = path.join(
      repoRoot,
      "data",
      "ops",
      "nfl-vegas-benchmark-report.json",
    );
    const raw = JSON.parse(readFileSync(reportPath, "utf-8"));
    return {
      generatedAt: raw.generated_at,
      modelVersion: raw.model_version,
      methodology: {
        summary: raw.methodology.summary,
        trainSeasons: raw.methodology.train_seasons,
        tuneSeasons: raw.methodology.tune_seasons,
        testSeasons: raw.methodology.test_seasons,
        testSampleSize: raw.methodology.test_sample_size,
        significanceTest: raw.methodology.significance_test,
        sourceScripts: raw.methodology.source_scripts ?? [],
        caveats: raw.methodology.caveats ?? [],
      },
      results2025Holdout: {
        spreadMae: raw.results_2025_holdout.spread_mae,
        totalMae: raw.results_2025_holdout.total_mae,
        winProbabilityBrier: raw.results_2025_holdout.win_probability_brier,
        spreadSignificance: {
          diff: raw.results_2025_holdout.spread_significance.diff,
          ci95Low: raw.results_2025_holdout.spread_significance.ci_95_low,
          ci95High: raw.results_2025_holdout.spread_significance.ci_95_high,
          significant: raw.results_2025_holdout.spread_significance.significant,
        },
      },
      resultsFull13YrSample: {
        seasons: raw.results_full_13yr_sample.seasons,
        sampleSize: raw.results_full_13yr_sample.sample_size,
        note: raw.results_full_13yr_sample.note,
        spreadMae: raw.results_full_13yr_sample.spread_mae,
        totalMae: raw.results_full_13yr_sample.total_mae,
      },
    };
  } catch {
    return null;
  }
}

export function percentBetter(model: number, vegas: number): number {
  if (!Number.isFinite(model) || !Number.isFinite(vegas) || vegas === 0)
    return 0;
  return ((vegas - model) / vegas) * 100;
}
