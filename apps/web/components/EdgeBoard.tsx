// components/EdgeBoard.tsx
import Link from "next/link";

type Variant = "home" | "full";
type Tag = "PLAY" | "LEAN" | "PASS";

export type PriceSide = { label: string; juice: string };
export type PricePair = { top: PriceSide; bottom: PriceSide };

export type TeamBlock = {
  name: string;
  keiRank?: string; // optional for now
  site: "Away" | "Home";
  record?: string;
  confRecord?: string;
};

export type EdgeBoardRow = {
  id: string;
  time?: string;

  teamA: TeamBlock;
  teamB: TeamBlock;

  openOU: PricePair;
  openLine: PricePair;

  bestLine: PricePair;
  bestOU: PricePair;

  // placeholders for future model
  keiLine?: PricePair;
  keiOU?: PricePair;

  edgeLine?: PricePair;
  edgeOU?: PricePair;

  tagLine?: Tag;
  tagOU?: Tag;
};

const COMING_SOON_PAIR: PricePair = {
  top: { label: "Coming soon", juice: "—" },
  bottom: { label: "Coming soon", juice: "—" },
};

const sampleRows: EdgeBoardRow[] = [
  {
    id: "sample-1",
    time: "8:30pm",
    teamA: { name: "Duke", keiRank: "12", site: "Away", record: "21-1", confRecord: "10-0" },
    teamB: { name: "UNC", keiRank: "18", site: "Home", record: "18-4", confRecord: "8-2" },

    openOU: {
      top: { label: "o150.5", juice: "-110" },
      bottom: { label: "u150.5", juice: "-110" },
    },
    openLine: {
      top: { label: "+5.5", juice: "-110" },
      bottom: { label: "-5.5", juice: "-110" },
    },

    bestLine: {
      top: { label: "+6.5", juice: "-112" },
      bottom: { label: "-5.0", juice: "-110" },
    },
    bestOU: {
      top: { label: "o149.5", juice: "-110" },
      bottom: { label: "u152.5", juice: "-112" },
    },
  },
];

function tagPill(tag?: Tag) {
  if (!tag) return "bg-white/5 text-gray-300 border-white/10";
  if (tag === "PLAY") return "bg-[#15803d]/20 text-[#22c55e] border-[#22c55e]/25";
  if (tag === "LEAN") return "bg-kos-gold/15 text-kos-gold border-kos-gold/25";
  return "bg-white/5 text-gray-300 border-white/10";
}

function PriceCell({
  p,
  valueClassName = "text-gray-200 font-semibold",
  compact = false,
}: {
  p: PricePair;
  valueClassName?: string;
  compact?: boolean;
}) {
  const sep = compact ? "mt-1 h-px" : "mt-1.5 h-px";
  const topPad = compact ? "mt-1" : "mt-1.5";
  const valueLeading = compact ? "leading-[1.05]" : "leading-tight";

  return (
    <div className={valueLeading}>
      <div className={valueClassName}>{p.top.label}</div>
      <div className="text-[11px] text-gray-400">({p.top.juice})</div>

      <div className={`${sep} bg-white/10`} />

      <div className={`${topPad} ${valueClassName}`}>{p.bottom.label}</div>
      <div className="text-[11px] text-gray-400">({p.bottom.juice})</div>
    </div>
  );
}

function HeaderStack({ a, b }: { a: string; b?: string }) {
  return (
    <div className="flex flex-col leading-[1.05]">
      <span>{a}</span>
      {b ? <span>{b}</span> : null}
    </div>
  );
}

export default function EdgeBoard({
  variant = "full",
  rows,
}: {
  variant?: Variant;
  rows?: EdgeBoardRow[];
}) {
  const edgeGreen =
    "text-[#22c55e] font-bold drop-shadow-[0_0_10px_rgba(34,197,94,0.55)]";

  const data = rows && rows.length ? rows : sampleRows;

  if (variant === "home") {
    // Keep homepage sample card
    return (
      <div className="lg:col-span-5">
        <div className="relative">
          <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-kos-gold/25 via-kos-green/15 to-kos-gold/25 blur-2xl opacity-80" />

          <div className="relative bg-black/40 border border-white/12 rounded-3xl p-5 sm:p-6 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-3xl font-bebas text-kos-gold">Edge Board</h2>
              <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-gray-400">
                Sample
              </span>
            </div>

            <div className="overflow-hidden rounded-2xl border border-white/10">
              <table className="w-full text-sm sm:text-base">
                <thead className="bg-white/5">
                  <tr className="text-left text-gray-300">
                    <th className="py-2.5 px-3">Game</th>
                    <th className="py-2.5 px-3">Best Line</th>
                    <th className="py-2.5 px-3">Best O/U</th>
                    <th className="py-2.5 px-3">Edge</th>
                    <th className="py-2.5 px-3">Tag</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-white/10 text-gray-200">
                  {sampleRows.map((r) => (
                    <tr key={r.id} className="hover:bg-white/5 transition">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold">
                          {r.teamA.name} vs {r.teamB.name}
                        </div>
                        <div className="text-[11px] text-gray-400">
                          {r.teamA.name} ({r.teamA.keiRank ?? "—"}) • {r.teamB.name} ({r.teamB.keiRank ?? "—"})
                        </div>
                      </td>
                      <td className="py-2.5 px-3">{r.bestLine.top.label}</td>
                      <td className="py-2.5 px-3">{r.bestOU.top.label}</td>
                      <td className={["py-2.5 px-3", edgeGreen].join(" ")}>Coming soon</td>
                      <td className="py-2.5 px-3 font-bebas text-kos-gold tracking-wide">Coming soon</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 text-xs text-gray-400">Sample data for illustrative purposes only.</div>
          </div>
        </div>
      </div>
    );
  }

  // FULL variant
  return (
    <div className="mt-6 hidden lg:block">
      <div className="bg-black/30 border border-white/12 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="text-sm text-gray-300">Tonight • Live odds (Open + Best) • Everything else coming soon</div>
          <div className="text-xs text-gray-500">Logos + links next</div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full table-fixed text-[12.75px] tabular-nums">
            <colgroup>
              <col style={{ width: "160px" }} /> {/* Game */}
              <col style={{ width: "85px" }} />  {/* Time */}
              <col style={{ width: "85px" }} />  {/* Open O/U */}
              <col style={{ width: "85px" }} />  {/* Open Line */}
              <col style={{ width: "85px" }} />  {/* Best Line */}
              <col style={{ width: "85px" }} />  {/* Best O/U */}
              <col style={{ width: "85px" }} />  {/* KEICMB Line */}
              <col style={{ width: "85px" }} />  {/* KEICMB O/U */}
              <col style={{ width: "75px" }} />  {/* Edge Line */}
              <col style={{ width: "75px" }} />  {/* Edge O/U */}
              <col style={{ width: "75px" }} />  {/* Tag Line */}
              <col style={{ width: "75px" }} />  {/* Tag O/U */}
            </colgroup>

            <thead className="bg-white/5 text-gray-300 uppercase tracking-wide text-[13px]">
              <tr className="text-left">
                <th className="py-2.5 px-3"><HeaderStack a="Game" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="Time" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="Open" b="O/U" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="Open" b="Line" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="Best" b="Line" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="Best" b="O/U" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="KEICMB" b="Line" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="KEICMB" b="O/U" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="Edge" b="Line" /></th>
                <th className="py-2.5 px-3"><HeaderStack a="Edge" b="O/U" /></th>
                <th className="py-2.5 px-3 text-center"><HeaderStack a="Tag" b="Line" /></th>
                <th className="py-2.5 px-3 text-center"><HeaderStack a="Tag" b="O/U" /></th>
              </tr>
            </thead>

            <tbody className="divide-y divide-white/10 text-gray-200">
              {data.map((r) => (
                <tr key={r.id} className="hover:bg-white/5 transition">
                  {/* Game */}
                  <td className="py-2.5 px-3 align-top relative pb-7">
                    <div className="font-semibold truncate">
                      {r.teamA.name}{" "}
                      <span className="text-gray-400">({r.teamA.keiRank ?? "—"})</span>
                    </div>
                    <div className="text-xs text-gray-400">
                      {r.teamA.site}
                      {r.teamA.record ? ` • ${r.teamA.record}` : ""}
                      {r.teamA.confRecord ? ` (${r.teamA.confRecord})` : ""}
                    </div>

                    <div className="mt-1 font-semibold truncate">
                      {r.teamB.name}{" "}
                      <span className="text-gray-400">({r.teamB.keiRank ?? "—"})</span>
                    </div>
                    <div className="text-xs text-gray-400">
                      {r.teamB.site}
                      {r.teamB.record ? ` • ${r.teamB.record}` : ""}
                      {r.teamB.confRecord ? ` (${r.teamB.confRecord})` : ""}
                    </div>

                    <button
                      className="absolute bottom-2 left-3 text-[14px] text-kos-gold hover:underline whitespace-nowrap"
                      type="button"
                      title="Expandable panel coming soon"
                    >
                      Overview ▾
                    </button>
                  </td>

                  {/* Time */}
                  <td className="py-2.5 px-1 align-top relative pb-7 overflow-hidden">
                    <div className="text-sm font-medium text-gray-300 whitespace-nowrap">
                      {r.time ?? "—"}
                    </div>
                    <button
                      className="absolute bottom-2 left-0 right-0 mx-auto text-center text-[14px] text-kos-gold hover:text-kos-gold transition whitespace-nowrap"
                      type="button"
                      title="Expandable panel coming soon"
                    >
                      Stats ▾
                    </button>
                  </td>

                  {/* Live odds columns */}
                  <td className="py-2.5 px-3 align-top text-gray-400">
                    <PriceCell p={r.openOU} compact valueClassName="text-gray-400 font-medium" />
                  </td>
                  <td className="py-2.5 px-3 align-top text-gray-400">
                    <PriceCell p={r.openLine} compact valueClassName="text-gray-400 font-medium" />
                  </td>
                  <td className="py-2.5 px-3 align-top">
                    <PriceCell p={r.bestLine} compact valueClassName="text-gray-100 font-semibold" />
                  </td>
                  <td className="py-2.5 px-3 align-top">
                    <PriceCell p={r.bestOU} compact valueClassName="text-gray-100 font-semibold" />
                  </td>

                  {/* Coming soon columns */}
                  <td className="py-2.5 px-2 align-top">
                    <PriceCell p={COMING_SOON_PAIR} compact valueClassName="text-gray-500 font-medium" />
                  </td>
                  <td className="py-2.5 px-2 align-top">
                    <PriceCell p={COMING_SOON_PAIR} compact valueClassName="text-gray-500 font-medium" />
                  </td>

                  <td className="py-2.5 px-2 align-top">
                    <PriceCell p={COMING_SOON_PAIR} compact valueClassName="text-gray-500 font-medium" />
                  </td>
                  <td className="py-2.5 px-2 align-top">
                    <PriceCell p={COMING_SOON_PAIR} compact valueClassName="text-gray-500 font-medium" />
                  </td>

                  <td className="py-2.5 px-2 align-top text-center">
                    <span className="inline-flex items-center justify-center px-2 py-1 rounded-lg border text-[12px] font-semibold bg-white/5 text-gray-300 border-white/10">
                      Coming soon
                    </span>
                  </td>
                  <td className="py-2.5 px-2 align-top text-center">
                    <span className="inline-flex items-center justify-center px-2 py-1 rounded-lg border text-[12px] font-semibold bg-white/5 text-gray-300 border-white/10">
                      Coming soon
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 text-[10px] text-gray-400 border-t border-white/10">
          Live: Game/Time/Open/Best. Coming soon: KEICMB + Edge + Tags, sportsbook logos + deep links, Overview/Stats expanders.
        </div>
      </div>
    </div>
  );
}