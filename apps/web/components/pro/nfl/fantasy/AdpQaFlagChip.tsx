import type { AdpQaFlag } from "@/lib/fantasy/adp-qa-flags";

export function AdpQaFlagChip({
  flag,
  className = "",
}: {
  flag: AdpQaFlag | null | undefined;
  className?: string;
}) {
  if (!flag) return null;
  const tone =
    flag.kind === "model_ahead"
      ? "border-kos-gold/40 bg-kos-gold/10 text-kos-gold"
      : "border-rose-300/40 bg-rose-300/10 text-rose-200";
  const title = [
    flag.categoryLabel,
    `|Δ| ${flag.absGap.toFixed(0)} (threshold ${flag.threshold})`,
    flag.preseason ? "preseason sim" : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-semibold leading-tight ${tone} ${className}`}
      title={title}
      data-testid="adp-qa-flag"
      data-qa-kind={flag.kind}
    >
      <span className="uppercase tracking-[0.08em] text-[9px] opacity-80">
        {flag.categoryLabel}
      </span>
      <span>{flag.label}</span>
    </span>
  );
}
