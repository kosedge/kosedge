import type { InsightSection } from "../types";
import type { PillarMeta } from "../types";
import { getProInsightWeekIndex } from "../rotation";
import * as p1 from "./pillar1";
import * as p2 from "./pillar2";
import * as p3 from "./pillar3";
import * as p4 from "./pillar4";
import * as p5 from "./pillar5";
import * as p6 from "./pillar6";
import * as p7 from "./pillar7";

const PILLARS = [
  [p1.section1, p1.section2, p1.section3, p1.section4],
  [p2.section1, p2.section2, p2.section3, p2.section4],
  [p3.section1, p3.section2, p3.section3, p3.section4],
  [p4.section1, p4.section2, p4.section3, p4.section4],
  [p5.section1, p5.section2, p5.section3, p5.section4],
  [p6.section1, p6.section2, p6.section3, p6.section4],
  [p7.section1, p7.section2, p7.section3, p7.section4],
] as const;

const PILLAR_METAS: PillarMeta[] = [
  { number: 1, title: "Why Most Bettors Lose (And It's Not What They Think)", isPro: false },
  { number: 2, title: "What \"Edge\" Actually Means", isPro: false },
  { number: 3, title: "Model: How We Measure Ourselves", isPro: false },
  { number: 4, title: "Best Line Shopping Is Non-Negotiable", isPro: false },
  { number: 5, title: "Discipline > Confidence", isPro: true },
  { number: 6, title: "Understanding Variance", isPro: true },
  { number: 7, title: "Deep Dive: How the MLB Simulation Works (Framework Only)", isPro: true },
];

/** Get section for pillar (1–7) and section index (1–4). */
export function getSection(pillarNum: number, sectionNum: number): InsightSection | null {
  const p = PILLARS[pillarNum - 1];
  const s = sectionNum >= 1 && sectionNum <= 4 ? sectionNum - 1 : 0;
  return p ? p[s] ?? null : null;
}

export function getPillarMeta(pillarNum: number): PillarMeta | null {
  return PILLAR_METAS[pillarNum - 1] ?? null;
}

export function getAllPillarMetas(): PillarMeta[] {
  return [...PILLAR_METAS];
}

/** Current Pro insight of the week (pillars 5, 6, 7 rotating). */
export function getProInsightOfWeek(): InsightSection | null {
  const idx = getProInsightWeekIndex();
  const pillarNum = 5 + Math.floor(idx / 4);
  const sectionNum = (idx % 4) + 1;
  return getSection(pillarNum, sectionNum);
}
