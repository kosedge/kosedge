import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { findTeamInDirectory } from "@/lib/team-research";
import {
  cfbTeamDisplayName,
  conferencePreviewHref,
  displayCfbConference,
} from "@/lib/cfb-conferences";
import { findCfbTeamPreview } from "@/lib/cfb-previews";
import {
  cfbPowerTeams,
  cfbResearchVersionStrip,
  findCfbPowerTeam,
  findCfbProjectionTeam,
  projectGameHref,
} from "@/lib/cfb-research-artifacts";
import {
  formatIndex,
  formatQbClassLabel,
} from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return cfbPowerTeams().map((row) => ({ team: row.team.toLowerCase() }));
}

export default async function CfbTeamDetailPage({
  params,
}: {
  params: Promise<{ team: string }>;
}) {
  const resolved = await params;
  const raw = String(resolved?.team || "").trim();
  const code = raw.toUpperCase();
  let power = findCfbPowerTeam(code);
  if (!power) {
    const dir = findTeamInDirectory("cfb", raw);
    if (dir?.code) {
      power = findCfbPowerTeam(dir.code);
      if (power && power.team.toLowerCase() !== raw.toLowerCase()) {
        redirect(`/pro/cfb/teams/${power.team.toLowerCase()}`);
      }
    }
  }
  if (!power) notFound();
  const proj = findCfbProjectionTeam(code);
  const preview = findCfbTeamPreview(code);
  const version = cfbResearchVersionStrip();
  const displayConf = displayCfbConference(power.team, power.conference);
  const confHref = conferencePreviewHref(displayConf);
  const nextHref = projectGameHref({ team: power.team, next: power.next });
  const name = cfbTeamDisplayName(power.team);

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title={name}
      summary={`${power.team} · ${displayConf} · power #${power.rank ?? "—"} · research DNA, next game, and preview when shipped.`}
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref={nextHref ?? "/pro/cfb/project-game"}
      primaryLabel={
        nextHref && power.next
          ? `Project W${power.next.week} ${power.next.opponent}`
          : "Project Game"
      }
      secondaryHref="/pro/cfb/teams"
      secondaryLabel="Power list"
    >
      <p className="mt-3 text-xs text-kos-text/55">
        {version.engine_version} · N={version.n_sims} · as_of {version.as_of} ·
        used_in_spread=false
      </p>

      <section className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-white/10 bg-black/35 px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
            Power
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-kos-text">
            {formatIndex(power.power_index, 3)}
          </p>
          <p className="text-xs text-kos-text/55">Rank {power.rank ?? "—"}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
            E[wins]
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-kos-text">
            {formatIndex(proj?.mean, 2)}
          </p>
          <p className="text-xs text-kos-text/55">
            {proj?.p10 != null && proj?.p90 != null
              ? `Band ${proj.p10.toFixed(0)}–${proj.p90.toFixed(0)} · E#${proj.rank}`
              : "No projection row"}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
            DNA
          </p>
          <p className="mt-1 text-sm text-kos-text">
            O {formatIndex(power.offense_index, 2)} / D{" "}
            {formatIndex(power.defense_index, 2)}
          </p>
          <p className="text-xs text-kos-text/55">
            σ {formatIndex(power.early_season_uncertainty, 2)}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
            QB
          </p>
          <p className="mt-1 text-sm text-kos-text">
            {power.qb_name || "—"}
          </p>
          <p className="text-xs text-kos-text/55">
            {formatQbClassLabel(power.qb_class)}
            {power.open_qb ? " · open job" : ""}
          </p>
        </div>
      </section>

      <section className="mt-4 rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-kos-text/75">
        <p>
          Conference{" "}
          {confHref ? (
            <Link href={confHref} className="font-semibold text-kos-gold">
              {displayConf}
            </Link>
          ) : (
            displayConf
          )}
          {displayConf !== (power.conference || "—") ? (
            <span className="ml-2 text-xs text-kos-text/45">
              (SoT said {power.conference})
            </span>
          ) : null}
        </p>
        <p className="mt-1 text-xs text-kos-text/55">
          Efficiency {power.efficiency_fill?.replace(/_/g, " ") || "—"}
          {power.efficiency_fill === "warehouse" ? " — warehouse fill, not silent 50/50." : ""}
        </p>
        {power.next ? (
          <p className="mt-2">
            Next: W{power.next.week} {power.next.home ? "vs" : "@"}{" "}
            {power.next.opponent}
            {power.next.neutral_site ? " (neutral)" : ""}
            {nextHref ? (
              <>
                {" · "}
                <Link href={nextHref} className="font-semibold text-kos-gold">
                  Open Project Game
                </Link>
              </>
            ) : (
              " · FCS / not an FBS Project Game row"
            )}
          </p>
        ) : (
          <p className="mt-2 text-kos-text/55">No next-game hook on this SoT row.</p>
        )}
      </section>

      {preview ? (
        <section className="mt-4 rounded-xl border border-kos-gold/25 bg-kos-gold/5 px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
            Preview
          </p>
          <h2 className="mt-1 text-lg font-semibold text-kos-text">
            {preview.title}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/75">
            {preview.bottomLine}
          </p>
          <Link
            href={`/pro/cfb/previews/${preview.slug}`}
            className="mt-3 inline-flex min-h-11 items-center text-sm font-semibold text-kos-gold"
          >
            Full preview →
          </Link>
        </section>
      ) : (
        <p className="mt-4 text-xs text-kos-text/50">
          No full preview shipped for this team yet (day bar is 8+). Template
          lives at /pro/cfb/previews.
        </p>
      )}
    </SportHubShell>
  );
}
