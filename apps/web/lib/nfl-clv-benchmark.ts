import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export type NflClvBenchmarkReport = {
  generatedAt: string;
  modelVersion: string;
  methodology: {
    summary: string;
    dataSource: string;
    seasonsIncluded: string;
    excluded: string;
    clvDefinition: string;
  };
  resultsBySeason: Array<{
    season: number;
    market: string;
    n: number;
    avgClv: number;
    positiveRate: number;
  }>;
  resultsCombined: {
    moneyline: { n: number; avgClv: number; positiveRate: number };
    total: { n: number; avgClv: number; positiveRate: number };
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

export function loadNflClvBenchmarkReport(): NflClvBenchmarkReport | null {
  try {
    const repoRoot = findRepoRoot();
    if (!repoRoot) return null;
    const reportPath = path.join(repoRoot, "data", "ops", "nfl-clv-benchmark-report.json");
    const raw = JSON.parse(readFileSync(reportPath, "utf-8"));
    return {
      generatedAt: raw.generated_at,
      modelVersion: raw.model_version,
      methodology: {
        summary: raw.methodology.summary,
        dataSource: raw.methodology.data_source,
        seasonsIncluded: raw.methodology.seasons_included,
        excluded: raw.methodology.excluded,
        clvDefinition: raw.methodology.clv_definition,
      },
      resultsBySeason: (raw.results_by_season ?? []).map((row: Record<string, unknown>) => ({
        season: row.season,
        market: row.market,
        n: row.n,
        avgClv: row.avg_clv,
        positiveRate: row.positive_rate,
      })),
      resultsCombined: {
        moneyline: {
          n: raw.results_combined_2024_2025.moneyline.n,
          avgClv: raw.results_combined_2024_2025.moneyline.avg_clv,
          positiveRate: raw.results_combined_2024_2025.moneyline.positive_rate,
        },
        total: {
          n: raw.results_combined_2024_2025.total.n,
          avgClv: raw.results_combined_2024_2025.total.avg_clv,
          positiveRate: raw.results_combined_2024_2025.total.positive_rate,
        },
      },
    };
  } catch {
    return null;
  }
}
