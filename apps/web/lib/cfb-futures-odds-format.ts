import { formatAmericanOdds } from "@/lib/american-odds";

export type CfbFutureOddsSnap = {
  american: number;
  impliedPct: number;
  book: string;
  asOfUtc: string | null;
};

export function formatCfbMarketOdds(snap: CfbFutureOddsSnap | null): string {
  return snap ? formatAmericanOdds(snap.american) : "—";
}

export function formatCfbImpliedPct(snap: CfbFutureOddsSnap | null): string {
  if (!snap || !Number.isFinite(snap.impliedPct)) return "—";
  return `${snap.impliedPct.toFixed(1)}%`;
}

export function formatCfbOddsAsOf(iso: string | null | undefined): string {
  if (!iso) return "—";
  return iso.replace("T", " ").replace(/\.\d+Z$/, "Z").replace("Z", " UTC");
}
