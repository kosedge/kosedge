import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";
import SiteFooter from "@/components/layout/SiteFooter";
import {
  formatJuice,
  formatSideLine,
  loadDeskRecord,
  type DeskRecordSummary,
  type DeskRecordTicket,
  type DeskRoiSummary,
  type DeskSegmentSummary,
} from "@/lib/desk-record";
import {
  getSport,
  resolveSportKey,
  sportDisplayLabel,
  type SportKey,
} from "@/lib/sports";

export const dynamic = "force-dynamic";

const RECORD_SPORTS: SportKey[] = ["cfb", "nfl"];
const SEASON = 2026;

type RecordView = "play" | "lean" | "all";

function parseView(raw: string | string[] | undefined): RecordView {
  const v = Array.isArray(raw) ? raw[0] : raw;
  if (v === "play" || v === "lean" || v === "all") return v;
  return "all";
}

function resultClass(result: DeskRecordTicket["result"]): string {
  if (result === "W") return "text-edge-green";
  if (result === "L") return "text-red-400";
  if (result === "P") return "text-kos-gold";
  return "text-white/55";
}

function RoiBlock({ roi }: { roi: DeskRoiSummary }) {
  if (roi.status === "DATA_GAP") {
    return (
      <div>
        <div className="text-2xl font-semibold tracking-tight text-kos-gold">
          DATA GAP
        </div>
        <p className="mt-1 text-sm text-white/60">
          {roi.note ??
            "ROI waits on stamped pre-kick juice — no flat −110 invent."}
        </p>
        <p className="mt-1 text-xs text-white/45">
          {roi.n_data_gap} settled W/L ticket
          {roi.n_data_gap === 1 ? "" : "s"} missing juice
        </p>
      </div>
    );
  }
  if (roi.status === "empty" || roi.roi == null) {
    return (
      <div>
        <div className="text-2xl font-semibold tracking-tight text-white/50">
          —
        </div>
        <p className="mt-1 text-sm text-white/60">
          {roi.note ?? "No settled ROI sample yet."}
        </p>
      </div>
    );
  }
  const pct = (roi.roi * 100).toFixed(1);
  const signed = roi.roi > 0 ? `+${pct}%` : `${pct}%`;
  return (
    <div>
      <div
        className={`text-2xl font-semibold tracking-tight ${
          roi.roi >= 0 ? "text-edge-green" : "text-red-400"
        }`}
      >
        {signed}
      </div>
      <p className="mt-1 text-sm text-white/60">
        {roi.profit_u != null && roi.profit_u > 0 ? "+" : ""}
        {roi.profit_u}u / {roi.risked_u}u risked · n={roi.n_tickets}
      </p>
      {roi.n_data_gap > 0 ? (
        <p className="mt-1 text-xs text-kos-gold/80">
          {roi.n_data_gap} ticket{roi.n_data_gap === 1 ? "" : "s"} excluded
          (juice DATA GAP)
        </p>
      ) : null}
    </div>
  );
}

function segmentFor(
  summary: DeskRecordSummary,
  view: RecordView,
): DeskSegmentSummary {
  if (view === "play") return summary.segments.play;
  if (view === "lean") return summary.segments.lean;
  return summary.segments.all;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ sport?: string }> | { sport?: string };
}) {
  const resolved =
    params && typeof (params as Promise<unknown>).then === "function"
      ? await (params as Promise<{ sport?: string }>)
      : ((params as { sport?: string }) ?? {});
  const sportKey = resolveSportKey(resolved?.sport, "cfb");
  const label = sportDisplayLabel(sportKey, "Sport");
  return {
    title: `${label} desk record`,
    description: `Kos Edge ${label} desk PLAY/LEAN ATS and ROI at best pre-kick juice. Public record — not a picks feed.`,
  };
}

export default async function DeskRecordPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport?: string }> | { sport?: string };
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const paramsPromise =
    params && typeof (params as Promise<unknown>).then === "function"
      ? (params as Promise<{ sport?: string }>)
      : Promise.resolve((params as { sport?: string }) ?? {});
  const searchPromise =
    searchParams &&
    typeof (searchParams as Promise<unknown>).then === "function"
      ? (searchParams as Promise<Record<string, string | string[] | undefined>>)
      : Promise.resolve(
          (searchParams as Record<string, string | string[] | undefined>) ?? {},
        );

  const [resolved, sp] = await Promise.all([paramsPromise, searchPromise]);
  const sportKey = resolveSportKey(resolved?.sport, "cfb") as SportKey;
  const view = parseView(sp.view);
  const sport = getSport(sportKey);
  const label = sportDisplayLabel(sportKey, "Sport");
  const supported = RECORD_SPORTS.includes(sportKey);
  const summary = supported
    ? loadDeskRecord(sportKey, SEASON)
    : loadDeskRecord("cfb", SEASON);
  const segment = segmentFor(summary, view);
  const empty = summary.n_tickets === 0;

  const viewHref = (v: RecordView) =>
    v === "all" ? `/record/${sportKey}` : `/record/${sportKey}?view=${v}`;

  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <article className="mx-auto max-w-5xl px-5 pt-10 pb-20 sm:px-6">
        <p className="text-xs uppercase tracking-[0.14em] text-white/45">
          Public desk record · {SEASON}
        </p>
        <h1 className="mt-2 text-4xl font-extrabold tracking-tight">
          {label} record
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-white/75">
          Season-to-date ATS and units for stamped desk <strong>PLAY</strong>{" "}
          and <strong>LEAN</strong> only. Edge Board tags that never made the
          desk card do not count. ROI uses best available pre-kick juice — never
          an invented flat −110.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {RECORD_SPORTS.map((s) => {
            const active = s === sportKey;
            return (
              <Link
                key={s}
                href={`/record/${s}${view === "all" ? "" : `?view=${view}`}`}
                className={
                  active
                    ? "rounded-xl bg-kos-gold px-4 py-2 text-sm font-semibold text-black"
                    : "rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 hover:border-kos-gold/40 hover:text-white"
                }
              >
                {sportDisplayLabel(s)}
              </Link>
            );
          })}
        </div>

        {!supported || (sport == null && sportKey !== "cfb") ? (
          <p className="mt-8 text-sm text-white/60">
            Unknown sport token. Use CFB or NFL.
          </p>
        ) : empty ? (
          <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
            <h2 className="text-lg font-semibold text-kos-gold">No tickets yet</h2>
            <p className="mt-2 text-sm leading-6 text-white/70">
              Honest empty — no desk PLAY/LEAN ledger rows for {label} {SEASON}.
              CFB Week 1 is seeded from desk packages; other sports stay blank
              until graded.
            </p>
          </section>
        ) : (
          <>
            <div
              className="mt-8 flex flex-wrap gap-2"
              role="tablist"
              aria-label="Record segment"
            >
              {(
                [
                  ["all", "All"],
                  ["play", "PLAY"],
                  ["lean", "LEAN"],
                ] as const
              ).map(([key, labelText]) => {
                const active = view === key;
                return (
                  <Link
                    key={key}
                    href={viewHref(key)}
                    role="tab"
                    aria-selected={active}
                    className={
                      active
                        ? "rounded-xl border border-edge-green/40 bg-edge-green/15 px-4 py-2 text-sm font-semibold text-edge-green"
                        : "rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 hover:border-white/25 hover:text-white"
                    }
                  >
                    {labelText}
                  </Link>
                );
              })}
            </div>

            <section className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="text-xs uppercase tracking-wide text-white/45">
                  {view === "play"
                    ? "PLAY ATS"
                    : view === "lean"
                      ? "LEAN ATS"
                      : "Combined ATS"}
                </div>
                <div className="mt-2 text-3xl font-semibold tracking-tight">
                  {segment.ats_str}
                </div>
                <p className="mt-1 text-xs text-white/45">
                  {view === "play"
                    ? "1.0u each"
                    : view === "lean"
                      ? "0.5u each"
                      : "PLAY 1.0u · LEAN 0.5u"}
                  {segment.n_open > 0
                    ? ` · ${segment.n_open} open`
                    : " · settled sample"}
                </p>
                {view === "all" ? (
                  <p className="mt-2 text-xs text-white/50">
                    PLAY {summary.play_ats_str} · LEAN {summary.lean_ats_str}
                  </p>
                ) : null}
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="text-xs uppercase tracking-wide text-white/45">
                  {view === "play"
                    ? "PLAY ROI"
                    : view === "lean"
                      ? "LEAN ROI"
                      : "Combined ROI"}
                </div>
                <div className="mt-2">
                  <RoiBlock roi={segment.roi} />
                </div>
              </div>
            </section>

            <section className="mt-10">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <h2 className="text-lg font-semibold text-kos-gold">
                  {view === "play"
                    ? "PLAY tickets"
                    : view === "lean"
                      ? "LEAN tickets"
                      : "All tickets"}
                </h2>
                <p className="text-xs text-white/45">
                  Ledger SoT · morning settle prior-day ET
                </p>
              </div>
              <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-white/45">
                      <th className="px-4 py-3 font-medium">Wk</th>
                      <th className="px-4 py-3 font-medium">Grade</th>
                      <th className="px-4 py-3 font-medium">Game / side</th>
                      <th className="px-4 py-3 font-medium">Book</th>
                      <th className="px-4 py-3 font-medium">Juice</th>
                      <th className="px-4 py-3 font-medium">Result</th>
                      <th className="px-4 py-3 font-medium text-right">u</th>
                    </tr>
                  </thead>
                  <tbody>
                    {segment.tickets.length === 0 ? (
                      <tr>
                        <td
                          colSpan={7}
                          className="px-4 py-6 text-sm text-white/55"
                        >
                          No {view === "lean" ? "LEAN" : "PLAY"} tickets in this
                          ledger yet.
                        </td>
                      </tr>
                    ) : (
                      segment.tickets.map((t) => (
                        <tr
                          key={t.ticket_id}
                          className="border-b border-white/5 last:border-0"
                        >
                          <td className="px-4 py-3 text-white/60">{t.week}</td>
                          <td className="px-4 py-3 font-medium text-kos-gold">
                            {t.grade}
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-white/90">{t.game}</div>
                            <div className="text-xs text-white/50">
                              {formatSideLine(t.side, t.line)}
                              {t.final_home != null && t.final_away != null
                                ? ` · final ${t.final_away}–${t.final_home}`
                                : ""}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-white/65">
                            {t.book ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-white/65">
                            {formatJuice(t.juice, t.juice_status)}
                          </td>
                          <td
                            className={`px-4 py-3 font-semibold ${resultClass(t.result)}`}
                          >
                            {t.result}
                          </td>
                          <td className="px-4 py-3 text-right text-white/70">
                            {t.profit_u == null
                              ? t.juice_status === "DATA_GAP" &&
                                (t.result === "W" || t.result === "L")
                                ? "DATA GAP"
                                : "—"
                              : t.profit_u > 0
                                ? `+${t.profit_u}`
                                : String(t.profit_u)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        <section className="mt-12 max-w-2xl text-sm leading-6 text-white/55">
          <h2 className="text-sm font-semibold text-white/80">Contract</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Desk PLAY/LEAN only — writer packages / stamped desk SoT.</li>
            <li>
              Segment views: PLAY-only, LEAN-only, and All — each with its own
              ATS + ROI.
            </li>
            <li>
              Best pre-kick number + juice among Compare Odds books; stamp
              as_of.
            </li>
            <li>Missing juice → DATA GAP for ROI; ATS still shown.</li>
            <li>Pushes: profit 0; stake out of risked.</li>
          </ul>
          <p className="mt-4">
            Ops note:{" "}
            <Link
              href="/methodology"
              className="text-kos-gold hover:underline"
            >
              Methodology
            </Link>
            {" · "}
            machine SoT under <code className="text-white/70">data/desk-record/</code>
            {" · "}
            <code className="text-white/70">docs/DESK_ATS_ROI_RECORD.md</code>
          </p>
        </section>
      </article>
      <SiteFooter />
    </main>
  );
}
