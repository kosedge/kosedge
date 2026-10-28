import { readFileSync } from "node:fs";
import path from "path";
import { describe, expect, it } from "vitest";

describe("S10 AUTHORIZED_JOB beat/worker unchanged", () => {
  const repo = path.resolve(process.cwd(), "../..");

  it("celerybeat still schedules pull_odds_snapshot on the odds queue", () => {
    const beat = readFileSync(
      path.join(repo, "services/model-service/src/celerybeat_schedule.py"),
      "utf8",
    );
    expect(beat).toContain("pull-odds-season-cadence");
    expect(beat).toContain("pull-odds-3am-refresh");
    expect(beat).toContain("TASK_PULL_ODDS_SNAPSHOT");
  });

  it("model-service Odds client remains the sanctioned acquirer", () => {
    const client = readFileSync(
      path.join(repo, "services/model-service/src/services/odds_api.py"),
      "utf8",
    );
    expect(client).toContain("https://api.the-odds-api.com/v4");
    expect(client).toContain("ODDS_API_KEY");
  });
});
