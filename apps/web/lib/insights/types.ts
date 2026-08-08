import type { SportKey } from "@/lib/sports";

/** Paragraph = string, bullet list = string[]. */
export type InsightBlock = string | string[];

/** @deprecated Legacy weekly pillar section shape. Prefer InsightArticle. */
export type InsightSection = {
  title: string;
  pillarTitle?: string;
  body: InsightBlock[];
};

/** @deprecated Legacy pillar metadata. Prefer InsightArticle. */
export type PillarMeta = {
  number: number;
  title: string;
  isPro: boolean;
};

export type InsightTier = "free" | "pro";

export type InsightKind = "doctrine" | "desk-note";

export type ProductLink = {
  label: string;
  href: string;
};

/**
 * Locked Insights article shape.
 * Title → date → Bottom line → Key points → Short body → What to do on KosEdge.
 */
export type InsightArticle = {
  slug: string;
  kind: InsightKind;
  title: string;
  /** ISO date YYYY-MM-DD — published or last updated. */
  updatedAt: string;
  tier: InsightTier;
  /** Sport tags when relevant. Empty/omitted = cross-sport / process. */
  sports?: SportKey[];
  /** Optional desk-note type tags (e.g. survivor, injury, market). */
  tags?: string[];
  /** 1–3 sentences. */
  bottomLine: string;
  keyPoints: string[];
  /** Short scannable body sections. */
  sections: Array<{
    heading: string;
    blocks: InsightBlock[];
  }>;
  /** How to use this on the live desk. */
  whatToDo: Array<{
    text: string;
    link?: ProductLink;
  }>;
  /** Free teaser when Pro-gated (desk notes). */
  teaser?: string;
};

export type InsightsTab = "this-week" | "doctrine" | "sports";
