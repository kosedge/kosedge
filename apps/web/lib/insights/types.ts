/** Paragraph = string, bullet list = string[]. */
export type InsightBlock = string | string[];

export type InsightSection = {
  title: string;
  /** Optional subtitle (e.g. pillar title). */
  pillarTitle?: string;
  body: InsightBlock[];
};

export type PillarMeta = {
  number: number;
  title: string;
  isPro: boolean;
};
