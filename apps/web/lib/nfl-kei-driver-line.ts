type KeiDriverFactor = {
  factor: string;
  reason?: string;
};

type KeiDriverLog = {
  skipped?: boolean;
  appliedFactors: KeiDriverFactor[];
  consideredNotApplied: KeiDriverFactor[];
};

const HONEST_FACTORS = new Set(["weather", "short_week", "rest", "travel", "ref"]);

function honestChip(factor: KeiDriverFactor): string {
  const reason = (factor.reason || "").trim();
  if (reason) return reason;
  return `${factor.factor} not applied`;
}

/** Applied KEI drivers plus honest not-applied chips (never fake weather/rest). */
export function keiRepriceDriverLine(log: KeiDriverLog | null): string | null {
  if (!log || log.skipped) return null;
  const applied = log.appliedFactors
    .filter((f) => f.factor !== "injury_net")
    .map((f) => f.reason || f.factor)
    .filter(Boolean);
  const seen = new Set<string>();
  const honest: string[] = [];
  for (const factor of log.consideredNotApplied) {
    if (!HONEST_FACTORS.has(factor.factor)) continue;
    const chip = honestChip(factor);
    const key = factor.factor;
    if (seen.has(key) || !chip) continue;
    seen.add(key);
    honest.push(chip);
  }
  const names = [...applied, ...honest];
  if (names.length === 0) return null;
  return names.slice(0, 6).join(" · ");
}
