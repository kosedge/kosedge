/**
 * How 2-leg results may be presented.
 * When adjustment is null, UI must never imply a correlation-adjusted joint.
 */

import type { JointCorrelationMeta } from "@/lib/line-curve/types";

export const INDEPENDENT_JOINT_HEADING =
  "Independence — not correlation-adjusted";

export const INDEPENDENT_JOINT_CAPTION =
  "Joint cover is the independent product of each leg’s cover/push/loss masses. This is not a correlated / same-game joint. Phase 2 will replace independence with an explicit correlation model.";

export function jointProbabilityCaption(meta: JointCorrelationMeta): string {
  if (meta.assumption !== "independent" || meta.adjustment != null) {
    const src = meta.adjustment?.source ?? "adjusted";
    return `Correlation-adjusted joint (${src}). ${meta.note}`;
  }
  return `${INDEPENDENT_JOINT_HEADING}. ${INDEPENDENT_JOINT_CAPTION}`;
}

export function jointCoverColumnLabel(meta: JointCorrelationMeta): string {
  if (meta.assumption !== "independent" || meta.adjustment != null) {
    return "Adj. joint cover";
  }
  return "Indep. joint cover";
}

export function impliesCorrelationAdjusted(meta: JointCorrelationMeta): boolean {
  return meta.assumption === "adjusted" && meta.adjustment != null;
}
