"use client";

type ChartPoint = {
  altLine: number;
  modelCoverProbability: number;
  impliedProbability: number;
};

function fmt(n: number): string {
  return n > 0 ? `+${n}` : String(n);
}

export default function LineCurveChart({ points }: { points: ChartPoint[] }) {
  if (points.length < 2) {
    return (
      <p className="text-xs text-kos-text/55">
        Need at least two posted alts to draw the curve.
      </p>
    );
  }

  const width = 640;
  const height = 260;
  const pad = { l: 48, r: 16, t: 16, b: 36 };
  const xs = points.map((p) => p.altLine);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const ys = points.flatMap((p) => [
    p.modelCoverProbability,
    p.impliedProbability,
  ]);
  const minY = Math.max(0, Math.min(...ys) - 0.04);
  const maxY = Math.min(1, Math.max(...ys) + 0.04);

  const xOf = (x: number) =>
    pad.l + ((x - minX) / (maxX - minX || 1)) * (width - pad.l - pad.r);
  const yOf = (y: number) =>
    pad.t + (1 - (y - minY) / (maxY - minY || 1)) * (height - pad.t - pad.b);

  const modelPath = points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"} ${xOf(p.altLine)} ${yOf(p.modelCoverProbability)}`,
    )
    .join(" ");
  const bookPath = points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"} ${xOf(p.altLine)} ${yOf(p.impliedProbability)}`,
    )
    .join(" ");

  const ticks = [0, 0.25, 0.5, 0.75, 1]
    .map((t) => minY + t * (maxY - minY))
    .filter((y) => y >= minY && y <= maxY);

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full max-w-3xl text-kos-text"
        role="img"
        aria-label="Alternate spread versus model cover and sportsbook implied probability"
      >
        {ticks.map((y) => (
          <g key={y}>
            <line
              x1={pad.l}
              x2={width - pad.r}
              y1={yOf(y)}
              y2={yOf(y)}
              stroke="rgba(255,255,255,0.08)"
            />
            <text
              x={pad.l - 8}
              y={yOf(y) + 3}
              textAnchor="end"
              className="fill-kos-text/45"
              fontSize="10"
            >
              {(y * 100).toFixed(0)}%
            </text>
          </g>
        ))}
        {points.map((p) => (
          <text
            key={p.altLine}
            x={xOf(p.altLine)}
            y={height - 10}
            textAnchor="middle"
            className="fill-kos-text/45"
            fontSize="10"
          >
            {fmt(p.altLine)}
          </text>
        ))}
        <path d={bookPath} fill="none" stroke="#f59e0b" strokeWidth="2" />
        <path d={modelPath} fill="none" stroke="#4ade80" strokeWidth="2.25" />
        {points.map((p) => (
          <g key={`d-${p.altLine}`}>
            <circle
              cx={xOf(p.altLine)}
              cy={yOf(p.impliedProbability)}
              r="3"
              fill="#f59e0b"
            />
            <circle
              cx={xOf(p.altLine)}
              cy={yOf(p.modelCoverProbability)}
              r="3"
              fill="#4ade80"
            />
          </g>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap gap-4 text-[11px] text-kos-text/60">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-4 rounded-sm bg-green-400" /> Model cover
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-4 rounded-sm bg-amber-400" /> Book implied
        </span>
      </div>
    </div>
  );
}
