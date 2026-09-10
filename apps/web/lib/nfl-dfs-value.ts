export type DfsValue = {
  pointsPer1k: number | null;
  salaryRelDelta: number | null;
  salaryRelPer1k: number | null;
  bandSize: number;
  bandMedianProjection: number | null;
};

export function pointsPer1k(
  projection: number | null | undefined,
  salary: number | null | undefined,
): number | null {
  if (projection == null || salary == null) return null;
  if (!(salary > 0) || !Number.isFinite(projection)) return null;
  return Math.round((projection / (salary / 1000)) * 10000) / 10000;
}

export function salaryRelativePositionalValue(input: {
  projection: number | null | undefined;
  salary: number | null | undefined;
  peerSalariesAndProjections: Array<[number, number]>;
}): DfsValue {
  const p1k = pointsPer1k(input.projection, input.salary);
  if (input.projection == null || input.salary == null || !(input.salary > 0)) {
    return {
      pointsPer1k: p1k,
      salaryRelDelta: null,
      salaryRelPer1k: null,
      bandSize: 0,
      bandMedianProjection: null,
    };
  }
  const peers = input.peerSalariesAndProjections.filter(([s]) => s > 0);
  if (peers.length < 2) {
    return {
      pointsPer1k: p1k,
      salaryRelDelta: null,
      salaryRelPer1k: null,
      bandSize: peers.length,
      bandMedianProjection: null,
    };
  }
  const lo = input.salary * 0.85;
  const hi = input.salary * 1.15;
  let band = peers.filter(([s]) => s >= lo && s <= hi);
  if (band.length < 3) {
    band = [...peers]
      .sort((a, b) => Math.abs(a[0] - input.salary!) - Math.abs(b[0] - input.salary!))
      .slice(0, 5);
  }
  if (band.length < 2) {
    return {
      pointsPer1k: p1k,
      salaryRelDelta: null,
      salaryRelPer1k: null,
      bandSize: band.length,
      bandMedianProjection: null,
    };
  }
  const sorted = [...band].map(([, y]) => y).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const bandMedian =
    sorted.length % 2 === 0
      ? (sorted[mid - 1]! + sorted[mid]!) / 2
      : sorted[mid]!;
  const delta = input.projection - bandMedian;
  return {
    pointsPer1k: p1k,
    salaryRelDelta: Math.round(delta * 10000) / 10000,
    salaryRelPer1k: Math.round((delta / (input.salary / 1000)) * 10000) / 10000,
    bandSize: band.length,
    bandMedianProjection: Math.round(bandMedian * 10000) / 10000,
  };
}
