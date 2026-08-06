"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useEffectEvent,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import { FantasyDeskNav } from "@/components/pro/nfl/fantasy/FantasyDeskNav";
import { formatAdp, valueLabel } from "@/lib/fantasy/adp-proxy";
import {
  advanceCpuUntilUserOrDone,
  autoCompleteDraft,
  availablePlayers,
  buildPostDraftReport,
  createMockDraftState,
  currentTeamIndex,
  defaultMockConfig,
  formatPickLabel,
  isDraftComplete,
  isUserTurn,
  makeUserPick,
  mockRosterNeeds,
  pickMeta,
  userRoster,
} from "@/lib/fantasy/mock-draft-engine";
import { MOCK_ROUNDS, type MockDraftState, type MockTeamCount } from "@/lib/fantasy/mock-types";
import {
  bestAvailableByNeed,
  bestAvailableByValue,
  type ValueAwareSuggestion,
} from "@/lib/fantasy/team-builder";
import type { FantasyDeskBoard, FantasyDeskRow, FantasyScoringProfile } from "@/lib/fantasy/types";
import {
  draftPositionBadgeClass,
  FANTASY_SCORING_PROFILES,
} from "@/lib/nfl-fantasy-draft-shared";

type Props = {
  board: FantasyDeskBoard;
  initialScoring?: FantasyScoringProfile;
  initialTeams?: MockTeamCount;
  initialSlot?: number;
};

const CPU_TICK_MS = 280;

export function FantasyMockDraftClient({
  board,
  initialScoring = "half_ppr",
  initialTeams = 12,
  initialSlot = 1,
}: Props) {
  const router = useRouter();
  const [teamCount, setTeamCount] = useState<MockTeamCount>(initialTeams);
  const [userSlot, setUserSlot] = useState(
    Math.min(Math.max(initialSlot, 1), initialTeams),
  );
  const [state, setState] = useState<MockDraftState | null>(null);
  const [query, setQuery] = useState("");
  const [posFilter, setPosFilter] = useState("ALL");
  const [busy, setBusy] = useState(false);
  const cpuTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scoring = board.scoringProfile || initialScoring;
  const emptyBoard = board.rows.length === 0;

  useEffect(() => {
    setUserSlot((slot) => Math.min(slot, teamCount));
  }, [teamCount]);

  const runCpuBurst = useEffectEvent((draft: MockDraftState) => {
    if (cpuTimer.current) clearTimeout(cpuTimer.current);
    if (isDraftComplete(draft) || isUserTurn(draft)) {
      setBusy(false);
      return;
    }
    setBusy(true);
    cpuTimer.current = setTimeout(() => {
      const next = advanceCpuUntilUserOrDone(board.rows, draft, 1);
      setState(next);
      if (!isDraftComplete(next) && !isUserTurn(next)) {
        runCpuBurst(next);
      } else {
        setBusy(false);
      }
    }, CPU_TICK_MS);
  });

  useEffect(() => {
    return () => {
      if (cpuTimer.current) clearTimeout(cpuTimer.current);
    };
  }, []);

  function startDraft() {
    if (emptyBoard) return;
    const config = defaultMockConfig(teamCount, scoring, userSlot);
    let draft = createMockDraftState({ config, board: board.rows });
    draft = advanceCpuUntilUserOrDone(board.rows, draft, 1);
    setState(draft);
    setQuery("");
    setPosFilter("ALL");
    if (!isUserTurn(draft) && !isDraftComplete(draft)) {
      runCpuBurst(draft);
    }
  }

  function resetToSetup() {
    if (cpuTimer.current) clearTimeout(cpuTimer.current);
    setBusy(false);
    setState(null);
  }

  function onPick(playerId: string) {
    if (!state || busy || !isUserTurn(state)) return;
    try {
      let next = makeUserPick(board.rows, state, playerId);
      setState(next);
      if (!isDraftComplete(next) && !isUserTurn(next)) {
        runCpuBurst(next);
      }
    } catch {
      // ignore stale taps
    }
  }

  function onAutoPickToEnd() {
    if (!state || isDraftComplete(state)) return;
    if (cpuTimer.current) clearTimeout(cpuTimer.current);
    setBusy(false);
    const finished = autoCompleteDraft(board.rows, state);
    setState(finished);
  }

  function changeScoring(next: FantasyScoringProfile) {
    const params = new URLSearchParams();
    params.set("scoring", next);
    params.set("teams", String(teamCount));
    params.set("slot", String(userSlot));
    router.push(`/pro/nfl/fantasy/mock?${params.toString()}`);
  }

  if (!state) {
    return (
      <SetupView
        board={board}
        teamCount={teamCount}
        userSlot={userSlot}
        scoring={scoring}
        emptyBoard={emptyBoard}
        onTeamCount={setTeamCount}
        onSlot={setUserSlot}
        onScoring={changeScoring}
        onStart={startDraft}
      />
    );
  }

  if (state.phase === "results" || isDraftComplete(state)) {
    return (
      <ResultsView
        board={board}
        state={state}
        onAgain={resetToSetup}
        onDesk={() => router.push(`/pro/nfl/fantasy?scoring=${scoring}`)}
      />
    );
  }

  return (
    <LiveView
      board={board}
      state={state}
      busy={busy}
      query={query}
      posFilter={posFilter}
      onQuery={setQuery}
      onPosFilter={setPosFilter}
      onPick={onPick}
      onAbort={resetToSetup}
      onAutoPickToEnd={onAutoPickToEnd}
    />
  );
}

function SetupView({
  board,
  teamCount,
  userSlot,
  scoring,
  emptyBoard,
  onTeamCount,
  onSlot,
  onScoring,
  onStart,
}: {
  board: FantasyDeskBoard;
  teamCount: MockTeamCount;
  userSlot: number;
  scoring: FantasyScoringProfile;
  emptyBoard: boolean;
  onTeamCount: (n: MockTeamCount) => void;
  onSlot: (n: number) => void;
  onScoring: (s: FantasyScoringProfile) => void;
  onStart: () => void;
}) {
  const hasKd = board.rows.some((r) =>
    ["K", "DST"].includes(r.position.toUpperCase()),
  );

  return (
    <div className="space-y-5">
      <section className="relative overflow-hidden rounded-3xl border border-kos-gold/30 bg-[radial-gradient(ellipse_at_top_left,_rgba(212,175,55,0.18),_transparent_55%),linear-gradient(145deg,#0b0d10_0%,#12151c_45%,#0a0c10_100%)] p-6 sm:p-8">
        <div className="relative">
          <p className="font-bebas text-5xl leading-none tracking-[0.04em] text-kos-gold sm:text-6xl">
            KOSEDGE
          </p>
          <h1 className="mt-2 font-bebas text-3xl tracking-wide text-kos-text sm:text-4xl">
            Mock Draft Room
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-kos-text/75 sm:text-base">
            Snake mocks on KosEdge rankings + FantasyPros ADP. You pick your
            seat; CPU fills every other team. Fast practice — no live league
            sync.
          </p>
          <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-kos-text/45">
            {board.season} · {board.adpSourceLabel} · {MOCK_ROUNDS} rounds
          </p>
        </div>
      </section>

      <FantasyDeskNav active="mock" scoring={scoring} />

      {board.source === "preseason-fallback" ? (
        <HonestStatusBanner title="Preseason board" tone="sky">
          <p>
            Skill-position rankings from the season-engine preseason sim. CPU
            still mixes model rank with market ADP when matched.
          </p>
        </HonestStatusBanner>
      ) : null}

      {!hasKd && !emptyBoard ? (
        <HonestStatusBanner title="K / DST unavailable" tone="amber">
          <p>
            Kickers and defenses aren&apos;t on this board — those roster slots
            are skipped in the mock and do not ding your grade.
          </p>
        </HonestStatusBanner>
      ) : null}

      {emptyBoard ? (
        <HonestStatusBanner title="Mock board empty" tone="neutral">
          <p>
            No players loaded for this scoring format. Open{" "}
            <Link
              href={`/pro/nfl/fantasy?scoring=${scoring}`}
              className="font-semibold text-kos-text underline underline-offset-2"
            >
              Rankings
            </Link>{" "}
            first, then come back to start a mock.
          </p>
        </HonestStatusBanner>
      ) : (
        <section className="rounded-2xl border border-white/10 bg-black/30 p-5 sm:p-6">
          <h2 className="text-lg font-semibold text-kos-text">League setup</h2>
          <p className="mt-1 text-sm text-kos-text/60">
            Teams, scoring, your slot — then draft manually while CPU handles
            everyone else.
          </p>

          <div className="mt-5 grid gap-5 sm:grid-cols-3">
            <Field label="Teams">
              <div className="flex gap-2">
                {([10, 12] as const).map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => onTeamCount(n)}
                    className={`min-h-11 flex-1 rounded-xl border px-3 py-2.5 text-sm font-semibold active:scale-[0.98] ${
                      teamCount === n
                        ? "border-kos-gold/50 bg-kos-gold/15 text-kos-gold"
                        : "border-white/15 bg-white/5 text-kos-text/70"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Scoring">
              <div className="flex flex-wrap gap-2">
                {FANTASY_SCORING_PROFILES.map((profile) => (
                  <button
                    key={profile.value}
                    type="button"
                    onClick={() => onScoring(profile.value)}
                    className={`min-h-11 rounded-xl border px-3 py-2.5 text-sm font-semibold active:scale-[0.98] ${
                      scoring === profile.value
                        ? "border-kos-gold/50 bg-kos-gold/15 text-kos-gold"
                        : "border-white/15 bg-white/5 text-kos-text/70"
                    }`}
                  >
                    {profile.label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Your draft slot">
              <select
                value={userSlot}
                onChange={(e) => onSlot(Number(e.target.value))}
                className="min-h-11 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm font-semibold text-kos-text"
              >
                {Array.from({ length: teamCount }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>
                    Slot {n} of {teamCount}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <p className="text-sm font-semibold text-kos-text">
              Mode · CPU others only
            </p>
            <p className="mt-1 text-xs text-kos-text/55">
              You pick every time your seat is on the clock. CPU fills all other
              teams. Use <span className="text-kos-text/75">Auto-pick to end</span>{" "}
              mid-draft if you want the room finished for you (including your
              remaining picks).
            </p>
          </div>

          <ul className="mt-5 list-disc space-y-1 pl-5 text-xs text-kos-text/55">
            <li>
              Roster: QB / 2 RB / 2 WR / TE / FLEX
              {hasKd ? " / DST / K" : " (no K/DST on this board)"} + bench
              through {MOCK_ROUNDS} rounds.
            </li>
            <li>
              CPU mixes ADP, KosEdge value, and need — not pure BPA and not
              random. Late-round QB2 stacking is suppressed once a starter is
              rostered.
            </li>
            <li>
              Board: {board.count} players · ADP matched{" "}
              {board.adpMatchedHighCount} high /{" "}
              {board.adpMatchedCrossFormatCount} cross-format ·{" "}
              {board.adpFreshnessLabel}.
            </li>
          </ul>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onStart}
              className="min-h-12 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-5 py-3 text-sm font-semibold text-kos-gold transition hover:bg-kos-gold/25 active:scale-[0.98]"
            >
              Start Mock
            </button>
            <Link
              href={`/pro/nfl/fantasy/builder?scoring=${scoring}`}
              className="min-h-12 rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
            >
              ← Builder
            </Link>
            <Link
              href={`/pro/nfl/fantasy?scoring=${scoring}`}
              className="min-h-12 rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
            >
              Rankings
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}

function LiveView({
  board,
  state,
  busy,
  query,
  posFilter,
  onQuery,
  onPosFilter,
  onPick,
  onAbort,
  onAutoPickToEnd,
}: {
  board: FantasyDeskBoard;
  state: MockDraftState;
  busy: boolean;
  query: string;
  posFilter: string;
  onQuery: (q: string) => void;
  onPosFilter: (p: string) => void;
  onPick: (id: string) => void;
  onAbort: () => void;
  onAutoPickToEnd: () => void;
}) {
  const [rosterOpen, setRosterOpen] = useState(false);
  const userTurn = isUserTurn(state);
  const teamIdx = currentTeamIndex(state);
  const roster = useMemo(
    () => userRoster(board.rows, state),
    [board.rows, state],
  );
  const needs = useMemo(
    () => mockRosterNeeds(roster, board.rows),
    [roster, board.rows],
  );
  const needChips = Object.entries(needs).filter(([, n]) => n > 0);
  const rosterSet = useMemo(
    () => new Set(roster.map((r) => r.playerId)),
    [roster],
  );
  const available = useMemo(
    () => availablePlayers(board.rows, state),
    [board.rows, state],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return available.filter((row) => {
      if (posFilter !== "ALL" && row.position.toUpperCase() !== posFilter) {
        return false;
      }
      if (!q) return true;
      return (
        row.playerName.toLowerCase().includes(q) ||
        row.team.toLowerCase().includes(q) ||
        row.position.toLowerCase().includes(q)
      );
    });
  }, [available, query, posFilter]);

  const byValue = bestAvailableByValue(available, rosterSet, 4, {
    pickOverall: state.nextOverall,
    roster,
  });
  const byNeed = bestAvailableByNeed(available, roster, 4, {
    pickOverall: state.nextOverall,
  });
  const recent = state.picks.slice(-10).reverse();
  const pickLabel = formatPickLabel(
    state.nextOverall,
    state.config.teamCount,
  );
  const onClock =
    teamIdx != null ? state.teamNames[teamIdx] ?? `Team ${teamIdx + 1}` : "—";
  const hasKd = board.rows.some((r) =>
    ["K", "DST"].includes(r.position.toUpperCase()),
  );
  const posChips = hasKd
    ? ["ALL", "QB", "RB", "WR", "TE", "K", "DST"]
    : ["ALL", "QB", "RB", "WR", "TE"];
  const emptyPosMsg =
    posFilter === "K" || posFilter === "DST"
      ? `${posFilter} isn’t on this board (preseason / skill-only). Slots are skipped — pick skill depth instead.`
      : "No players match this filter.";

  return (
    <div className="space-y-3 sm:space-y-4">
      <div className="sticky top-0 z-30 -mx-4 space-y-2 bg-[#0a0c10]/px-4 py-2 sm:static sm:mx-0 sm:bg-transparent sm:px-0 sm:py-0">
        <header className="rounded-2xl border border-kos-gold/30 bg-kos-gold/10 px-4 py-3 sm:px-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-[0.14em] text-kos-gold">
                {userTurn
                  ? "Your pick · CPU others only"
                  : busy
                    ? "CPU picking…"
                    : "On the clock"}
              </p>
              <p className="mt-0.5 text-base font-semibold text-kos-text sm:text-lg">
                Pick {pickLabel} · {state.nextOverall}/{state.totalPicks} ·{" "}
                {onClock}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <button
                type="button"
                onClick={onAutoPickToEnd}
                disabled={busy}
                title="CPU completes every remaining pick, including yours"
                className="min-h-10 rounded-lg border border-kos-gold/40 bg-kos-gold/15 px-3 py-2 text-xs font-semibold text-kos-gold disabled:opacity-40 active:scale-[0.98]"
              >
                Auto-pick to end
              </button>
              <button
                type="button"
                onClick={onAbort}
                className="min-h-10 rounded-lg border border-white/15 px-3 py-2 text-xs font-semibold text-kos-text/70"
              >
                Leave mock
              </button>
            </div>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-black/40">
            <div
              className="h-full rounded-full bg-kos-gold transition-all"
              style={{
                width: `${Math.min(100, ((state.nextOverall - 1) / state.totalPicks) * 100)}%`,
              }}
            />
          </div>
        </header>

        {/* Compact sticky roster / needs — always visible on mobile */}
        <section className="rounded-xl border border-white/10 bg-[#10131a]/p-3 shadow-lg shadow-black/40 sm:hidden">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-kos-text/45">
                Needs · {roster.length} rostered
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {needChips.length > 0 ? (
                  needChips.map(([pos, n]) => (
                    <span
                      key={pos}
                      className="rounded border border-rose-400/35 bg-rose-400/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose-100"
                    >
                      {pos}×{n}
                    </span>
                  ))
                ) : (
                  <span className="text-[10px] text-kos-text/50">
                    Starters covered
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setRosterOpen((v) => !v)}
              className="shrink-0 rounded-md border border-white/15 px-2 py-1 text-[11px] font-semibold text-kos-text/70"
            >
              {rosterOpen ? "Hide" : "Roster"}
            </button>
          </div>
          {rosterOpen ? (
            <ul className="mt-2 max-h-36 space-y-1 overflow-y-auto border-t border-white/10 pt-2">
              {roster.length === 0 ? (
                <li className="text-xs text-kos-text/50">No picks yet.</li>
              ) : (
                roster.map((row) => (
                  <li
                    key={row.playerId}
                    className="flex justify-between gap-2 text-xs"
                  >
                    <span className="truncate font-medium text-kos-text">
                      {row.playerName}
                    </span>
                    <span className="shrink-0 text-kos-text/50">
                      {row.position}
                    </span>
                  </li>
                ))
              )}
            </ul>
          ) : roster.length > 0 ? (
            <p className="mt-1.5 truncate text-[11px] text-kos-text/55">
              {roster
                .slice(-4)
                .map((r) => `${r.position} ${r.playerName}`)
                .join(" · ")}
              {roster.length > 4 ? " …" : ""}
            </p>
          ) : null}
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-4">
          <section className="rounded-2xl border border-white/10 bg-black/30 p-4">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
                Available
              </h2>
              <p className="text-xs text-kos-text/45">{filtered.length} shown</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {posChips.map((pos) => (
                <button
                  key={pos}
                  type="button"
                  onClick={() => onPosFilter(pos)}
                  className={`min-h-9 rounded-lg border px-3 py-1.5 text-[11px] font-semibold active:scale-[0.98] ${
                    posFilter === pos
                      ? "border-kos-gold/40 bg-kos-gold/15 text-kos-gold"
                      : "border-white/10 text-kos-text/60"
                  }`}
                >
                  {pos}
                </button>
              ))}
              <input
                value={query}
                onChange={(e) => onQuery(e.target.value)}
                placeholder="Search"
                className="min-h-9 min-w-0 flex-1 rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-sm text-kos-text placeholder:text-kos-text/40 sm:max-w-xs"
              />
            </div>

            {!hasKd ? (
              <p className="mt-2 text-[11px] text-kos-text/45">
                K/DST unavailable on this board — those slots are skipped.
              </p>
            ) : null}

            {userTurn ? (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <SuggestRail
                  title="Best by value"
                  suggestions={byValue}
                  disabled={busy}
                  onPick={onPick}
                />
                <SuggestRail
                  title="Best by need"
                  suggestions={byNeed}
                  disabled={busy}
                  onPick={onPick}
                />
              </div>
            ) : (
              <p className="mt-3 text-sm text-kos-text/55">
                Waiting on {onClock} (CPU others only). Suggestions unlock on
                your turn — or Auto-pick to end.
              </p>
            )}

            {filtered.length === 0 ? (
              <p className="mt-3 rounded-xl border border-dashed border-white/15 p-4 text-sm text-kos-text/60">
                {emptyPosMsg}
              </p>
            ) : (
              <ul className="mt-3 max-h-[28rem] divide-y divide-white/10 overflow-y-auto rounded-xl border border-white/10">
                {filtered.slice(0, 60).map((row) => (
                  <li
                    key={row.playerId}
                    className="flex items-center gap-3 px-3 py-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-kos-text">
                        {row.playerName}
                      </p>
                      <p className="text-xs text-kos-text/55">
                        <span
                          className={`mr-1 inline-flex rounded border px-1 text-[10px] ${draftPositionBadgeClass(row.position)}`}
                        >
                          {row.position}
                          {row.rankPosition}
                        </span>
                        {row.team} · #{row.rankOverall} · ADP{" "}
                        {formatAdp(row.adp, 0)} ·{" "}
                        {valueLabel(row.valueDelta).text}
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled={!userTurn || busy}
                      onClick={() => onPick(row.playerId)}
                      className="min-h-10 shrink-0 rounded-lg border border-kos-gold/40 bg-kos-gold/15 px-3.5 py-2 text-xs font-semibold text-kos-gold disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.98]"
                    >
                      Draft
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Mobile: compact pick feed — desktop keeps full board */}
          <section className="rounded-2xl border border-white/10 bg-black/30 p-4 md:hidden">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
              Draft history
            </h2>
            <ul className="mt-3 max-h-56 space-y-2.5 overflow-y-auto">
              {recent.length === 0 ? (
                <li className="text-sm text-kos-text/50">Draft just started.</li>
              ) : (
                recent.map((pick) => (
                  <li
                    key={pick.overall}
                    className="flex items-baseline justify-between gap-2 border-b border-white/5 pb-2 text-sm last:border-0 last:pb-0"
                  >
                    <span className="min-w-0">
                      <span className="tabular-nums text-kos-text/45">
                        {formatPickLabel(pick.overall, state.config.teamCount)}
                      </span>{" "}
                      <span
                        className={
                          pick.isUser
                            ? "font-semibold text-kos-gold"
                            : "text-kos-text"
                        }
                      >
                        {pick.playerName}
                      </span>
                    </span>
                    <span className="shrink-0 text-[11px] text-kos-text/45">
                      {pick.position} · {state.teamNames[pick.teamIndex]}
                    </span>
                  </li>
                ))
              )}
            </ul>
          </section>

          <div className="hidden md:block">
            <DraftBoard state={state} />
          </div>
        </div>

        <aside className="hidden space-y-4 lg:sticky lg:top-24 lg:block lg:self-start">
          <section className="rounded-2xl border border-white/10 bg-black/30 p-4">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
              Your roster
            </h2>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {needChips.map(([pos, n]) => (
                <span
                  key={pos}
                  className="rounded border border-rose-400/30 bg-rose-400/10 px-2 py-0.5 text-[11px] text-rose-200"
                >
                  Need {pos}×{n}
                </span>
              ))}
              {needChips.length === 0 ? (
                <span className="text-[11px] text-kos-text/50">
                  Starters covered — drafting depth
                </span>
              ) : null}
            </div>
            <ul className="mt-3 max-h-64 space-y-1.5 overflow-y-auto">
              {roster.length === 0 ? (
                <li className="text-sm text-kos-text/50">No picks yet.</li>
              ) : (
                roster.map((row) => (
                  <li
                    key={row.playerId}
                    className="flex justify-between gap-2 text-sm"
                  >
                    <span className="truncate font-medium text-kos-text">
                      {row.playerName}
                    </span>
                    <span className="shrink-0 text-xs text-kos-text/50">
                      {row.position}
                    </span>
                  </li>
                ))
              )}
            </ul>
          </section>

          <section className="rounded-2xl border border-white/10 bg-black/30 p-4">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
              Recent picks
            </h2>
            <ul className="mt-3 space-y-2">
              {recent.length === 0 ? (
                <li className="text-sm text-kos-text/50">Draft just started.</li>
              ) : (
                recent.map((pick) => (
                  <li key={pick.overall} className="text-sm text-kos-text/80">
                    <span className="text-kos-text/45">
                      {formatPickLabel(pick.overall, state.config.teamCount)}
                    </span>{" "}
                    <span className={pick.isUser ? "text-kos-gold" : ""}>
                      {pick.playerName}
                    </span>
                    <span className="text-kos-text/45">
                      {" "}
                      · {state.teamNames[pick.teamIndex]}
                    </span>
                  </li>
                ))
              )}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}

function SuggestRail({
  title,
  suggestions,
  disabled,
  onPick,
}: {
  title: string;
  suggestions: ValueAwareSuggestion[];
  disabled: boolean;
  onPick: (id: string) => void;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/25 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-kos-text/45">
        {title}
      </p>
      <ul className="mt-2 space-y-1.5">
        {suggestions.length === 0 ? (
          <li className="text-xs text-kos-text/45">No suggestions</li>
        ) : (
          suggestions.map(({ row, timingHint, timing }) => (
            <li key={row.playerId}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onPick(row.playerId)}
                className="flex w-full flex-col gap-0.5 rounded-lg border border-white/10 px-2 py-1.5 text-left text-xs hover:border-kos-gold/40 disabled:opacity-40"
              >
                <span className="flex w-full items-center justify-between gap-2">
                  <span className="truncate font-semibold text-kos-text">
                    {row.playerName}
                  </span>
                  <span className="shrink-0 text-kos-text/50">
                    {row.position} · {valueLabel(row.valueDelta).text}
                  </span>
                </span>
                {timingHint ? (
                  <span
                    className={`text-[10px] ${
                      timing === "take_now"
                        ? "text-kos-gold"
                        : timing === "wait"
                          ? "text-sky-300/90"
                          : "text-kos-text/45"
                    }`}
                  >
                    {timingHint}
                  </span>
                ) : null}
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function DraftBoard({ state }: { state: MockDraftState }) {
  const { teamCount, rounds } = state.config;
  const byOverall = new Map(state.picks.map((p) => [p.overall, p]));
  const userTeam = state.config.userSlot - 1;

  return (
    <section className="overflow-hidden rounded-2xl border border-white/10 bg-black/30">
      <div className="border-b border-white/10 px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
          Draft board
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-max border-separate border-spacing-0 text-left">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-[#10131a] px-2 py-2 text-[10px] uppercase text-kos-text/45">
                Rd
              </th>
              {state.teamNames.map((name, i) => (
                <th
                  key={name + i}
                  className={`px-2 py-2 text-[10px] font-semibold uppercase ${
                    i === userTeam ? "text-kos-gold" : "text-kos-text/45"
                  }`}
                >
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rounds }, (_, roundIdx) => {
              const round = roundIdx + 1;
              return (
                <tr key={round}>
                  <td className="sticky left-0 z-10 border-t border-white/5 bg-[#0c0f14] px-2 py-1.5 text-xs font-semibold text-kos-text/50">
                    {round}
                  </td>
                  {Array.from({ length: teamCount }, (_, col) => {
                    // Column is team index; snake means pick order zigzags.
                    const pickInRound =
                      round % 2 === 1 ? col + 1 : teamCount - col;
                    const overall = (round - 1) * teamCount + pickInRound;
                    const pick = byOverall.get(overall);
                    const meta = pickMeta(overall, teamCount);
                    const isCurrent = state.nextOverall === overall;
                    return (
                      <td
                        key={`${round}-${col}`}
                        className={`max-w-[7.5rem] border-t border-white/5 px-1.5 py-1.5 align-top text-[11px] ${
                          isCurrent
                            ? "bg-kos-gold/20"
                            : meta.teamIndex === userTeam
                              ? "bg-kos-gold/5"
                              : ""
                        }`}
                      >
                        {pick ? (
                          <div>
                            <p
                              className={`truncate font-semibold ${
                                pick.isUser ? "text-kos-gold" : "text-kos-text"
                              }`}
                            >
                              {pick.playerName}
                            </p>
                            <p className="text-kos-text/45">
                              {pick.position} · {pick.team}
                            </p>
                          </div>
                        ) : (
                          <span className="text-kos-text/25">
                            {isCurrent ? "●" : "·"}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ResultsView({
  board,
  state,
  onAgain,
  onDesk,
}: {
  board: FantasyDeskBoard;
  state: MockDraftState;
  onAgain: () => void;
  onDesk: () => void;
}) {
  const report = useMemo(
    () => buildPostDraftReport(board.rows, state),
    [board.rows, state],
  );

  return (
    <div className="space-y-5">
      <FantasyDeskNav
        active="mock"
        scoring={board.scoringProfile}
      />
      <section className="rounded-3xl border border-kos-gold/30 bg-[linear-gradient(145deg,#0b0d10_0%,#12151c_45%,#0a0c10_100%)] p-6 sm:p-8">
        <p className="text-[11px] uppercase tracking-[0.14em] text-kos-gold">
          Mock complete
        </p>
        <div className="mt-2 flex flex-wrap items-end gap-4">
          <div>
            <h1 className="font-bebas text-4xl tracking-wide text-kos-text">
              Team grade {report.grade}
            </h1>
            <p className="mt-1 text-sm text-kos-text/70">{report.detail}</p>
            <p className="mt-2 text-[11px] text-kos-text/45">
              {state.config.teamCount}-team · {state.config.scoringProfile} ·
              slot {state.config.userSlot} · model {state.modelVersion}
            </p>
          </div>
          <div className="rounded-2xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-3 text-center">
            <p className="text-[10px] uppercase text-kos-gold/80">Starters</p>
            <p className="font-bebas text-3xl text-kos-gold">
              {report.starterPoints.toFixed(0)}
            </p>
            <p className="text-[10px] text-kos-text/50">proj pts</p>
          </div>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onAgain}
            className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-sm font-semibold text-kos-gold active:scale-[0.98]"
          >
            New Mock
          </button>
          <Link
            href={`/pro/nfl/fantasy/builder?scoring=${board.scoringProfile}`}
            className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-kos-text"
          >
            Builder
          </Link>
          <button
            type="button"
            onClick={onDesk}
            className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-kos-text"
          >
            Rankings
          </button>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <NoteBlock title="Strengths" items={report.strengths} tone="good" />
        <NoteBlock title="Weaknesses" items={report.weaknesses} tone="warn" />
        <NoteBlock
          title="Notable values"
          items={
            report.values.length
              ? report.values
              : ["No high-confidence value spikes this mock."]
          }
          tone="good"
        />
        <NoteBlock
          title="Notable reaches"
          items={
            report.reaches.length
              ? report.reaches
              : ["No big reaches vs market ADP."]
          }
          tone="warn"
        />
      </div>

      <section className="rounded-2xl border border-white/10 bg-black/30 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
          Your roster
        </h2>
        <ul className="mt-3 divide-y divide-white/10">
          {report.roster.map((row) => (
            <li
              key={row.playerId}
              className="flex items-center justify-between gap-3 py-2 text-sm"
            >
              <span className="font-semibold text-kos-text">{row.playerName}</span>
              <span className="text-xs text-kos-text/55">
                {row.position}
                {row.rankPosition} · #{row.rankOverall} · ADP{" "}
                {formatAdp(row.adp, 0)} · {row.medianPoints.toFixed(0)} pts
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function NoteBlock({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "good" | "warn";
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <h2
        className={`text-sm font-semibold uppercase tracking-[0.12em] ${
          tone === "good" ? "text-edge-green/80" : "text-amber-200/80"
        }`}
      >
        {title}
      </h2>
      <ul className="mt-2 space-y-1.5 text-sm text-kos-text/75">
        {items.map((item) => (
          <li key={item}>· {item}</li>
        ))}
      </ul>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/45">
        {label}
      </p>
      {children}
    </div>
  );
}
