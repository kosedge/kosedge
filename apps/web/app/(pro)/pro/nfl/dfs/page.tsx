import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import {
  NflDfsBoardTable,
  NflDfsDeskControls,
} from "@/components/pro/nfl/NflDfsDeskClient";
import { fetchNflDfsBoard } from "@/lib/nfl-dfs-board";
import {
  formatDfsNumber,
  formatSalary,
  type NflDfsSummaryCard,
} from "@/lib/nfl-dfs-types";
import { canonicalDfsSite } from "@/lib/nfl-dfs-identity";

const DEFAULT_SEASON = 2026;
const DEFAULT_WEEK = 1;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function summaryLine(
  card: NflDfsSummaryCard | null,
  kind: "proj" | "value" | "ceil",
) {
  if (!card) return "Unavailable — no certified row.";
  const metric =
    kind === "value"
      ? card.value == null
        ? "—"
        : formatDfsNumber(card.value, 2)
      : kind === "ceil"
        ? formatDfsNumber(card.ceiling)
        : formatDfsNumber(card.projection);
  return `${card.playerName} · ${card.position} ${card.team} vs ${card.opponent} · ${formatSalary(card.salary)} · ${metric}`;
}

export default async function NflDfsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const site = canonicalDfsSite(firstValue(search.site)) ?? "DK";
  const seasonRaw = Number(firstValue(search.season));
  const weekRaw = Number(firstValue(search.week));
  const season =
    Number.isFinite(seasonRaw) && seasonRaw >= 2010
      ? seasonRaw
      : DEFAULT_SEASON;
  const week =
    Number.isFinite(weekRaw) && weekRaw >= 1 && weekRaw <= 18
      ? weekRaw
      : DEFAULT_WEEK;
  const position = (firstValue(search.pos) ?? "").toUpperCase();
  const slateId = firstValue(search.slate) ?? "";

  const board = await fetchNflDfsBoard({
    season,
    week,
    site,
    slateId: slateId || undefined,
    position: position || undefined,
  });

  const hasRows = board.rows.length > 0;
  const siteLabel = site === "FD" ? "FanDuel" : "DraftKings";

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
          DFS research desk
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          DFS Board
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-kos-text/75">
          {siteLabel} classic scoring on the shared NFL player-production spine.
          Salary and opponent come from the ingested {siteLabel} slate — not
          season averages. Ownership and leverage stay unavailable until a
          defensible source exists. No optimizer. No betting tags.
        </p>
        <div className="mt-4">
          {hasRows ? (
            <HonestStatusBanner
              title={`${siteLabel} · Week ${week} priced slate`}
              tone="sky"
            >
              <p>
                {board.rows.length} certified rows. Value is points per $1K, not
                a KosEdge rating. Floor/ceiling appear only when the weekly
                distribution exists. Ownership hidden.
              </p>
            </HonestStatusBanner>
          ) : (
            <HonestStatusBanner
              title={
                board.status === "no_slate" ||
                board.status === "ambiguous_slate"
                  ? "No certified slate"
                  : "Slate not priced yet"
              }
              tone="amber"
            >
              <p>
                {board.error ??
                  "This desk does not fall back to season-rate projections. Ingest a DK or FD salary file for the selected week, then the board fills from weekly production."}
                {board.rejected.length
                  ? ` ${board.rejected.length} identity joins failed closed.`
                  : ""}
              </p>
            </HonestStatusBanner>
          )}
        </div>
      </section>

      <div className="mt-5">
        <NflDfsDeskControls
          season={season}
          week={week}
          site={site}
          position={position}
          slates={board.slates}
          slateId={board.slateId ?? slateId}
        />
      </div>

      <section className="mt-6 grid gap-3 md:grid-cols-3">
        <SummaryCard
          title="Top projection"
          body={summaryLine(board.summary.topProjection, "proj")}
        />
        <SummaryCard
          title="Best value"
          body={summaryLine(board.summary.bestValue, "value")}
        />
        <SummaryCard
          title="Highest ceiling"
          body={summaryLine(board.summary.highestCeiling, "ceil")}
        />
      </section>

      <section className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
        <NflDfsBoardTable rows={board.rows} />
      </section>
    </main>
  );
}

function SummaryCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/35 p-4">
      <h2 className="text-sm font-semibold text-kos-gold">{title}</h2>
      <p className="mt-3 text-sm text-kos-text/80">{body}</p>
    </div>
  );
}
