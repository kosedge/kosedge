import "server-only";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import {
  cardsFromDayFile,
  collectPreviewDeltas,
  collectSotFlags,
  partitionCampDeskShelf,
  type CampDeskCard,
  type CampDeskDayFile,
  type CampPreviewDelta,
} from "@/lib/nfl-camp-desk-daily";
import {
  espnItemIsCampRelevant,
  espnItemIsInjuryRelevant,
  fetchEspnNflArticles,
  type EspnNflNewsItem,
} from "@/lib/nfl-espn-news";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import { isNflCalendarPreseason, NFL_PRODUCT_SEASON } from "@/lib/nfl-truth-label";
import beatWritersJson from "../../../data/writers/nfl-beat-writers.json";

export type CampBeatLink = {
  team: string;
  teamName: string;
  division: string;
  kosEdgeWriter: string;
  primaryWriter: string | null;
  primaryOutlet: string | null;
  primaryHandle: string | null;
  espnCampHref: string | null;
  previewHref: string;
};

/** @deprecated Prefer EspnNflNewsItem — kept for Camp Desk payload typing. */
export type CampNewsItem = EspnNflNewsItem;

export type CampWriterIntelItem = {
  team: string;
  teamName: string;
  author: string;
  angle: string | null;
  campRefsMarkdown: string;
  previewHref: string;
  sourceLinks: Array<{ label: string; href: string }>;
};

export type CampDeskPayload = {
  generatedAt: string;
  eraLabel: string;
  hubHref: string;
  kosedgeCards: CampDeskCard[];
  archiveCards: CampDeskCard[];
  latestDeskDate: string | null;
  deskStale: boolean;
  sotFlags: CampDeskCard[];
  previewDelta: CampPreviewDelta[];
  rotationNext: string[];
  wire: CampNewsItem[];
  news: CampNewsItem[];
  injuryNews: CampNewsItem[];
  writerIntel: CampWriterIntelItem[];
  beats: CampBeatLink[];
  writers: Array<{ name: string; coverage: string }>;
  notes: string[];
  diagnostics: {
    newsCount: number;
    injuryNewsCount: number;
    writerIntelCount: number;
    beatCount: number;
    beatRegistryVersion: string | null;
    kosedgeCardCount: number;
    wireCount: number;
  };
};

type BeatRegistry = {
  version?: string;
  era?: string;
  updated?: string;
  teams?: Record<
    string,
    {
      team?: string;
      division?: string;
      kos_edge_writer?: string;
      writers?: Array<{
        name?: string;
        outlet?: string;
        x?: string[];
        role?: string;
      }>;
    }
  >;
};

const WRITER_COVERAGE: Array<{ name: string; coverage: string }> = [
  { name: "Casey Voss", coverage: "NFC North" },
  { name: "Reese Quinn", coverage: "AFC North, AFC West" },
  { name: "Morgan Hale", coverage: "NFC West" },
  { name: "Taylor Brooks", coverage: "AFC East, AFC South" },
  { name: "Avery Cole", coverage: "NFC South, NFC East" },
];

/** Known ESPN 2026 team camp hubs (public story pages). */
const ESPN_TEAM_CAMP_HUBS: Record<string, string> = {
  ARI: "https://www.espn.com/nfl/story/_/id/49426382/arizona-cardinals-training-camp-2026-intel-updates",
  ATL: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  BAL: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  BUF: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  CAR: "https://www.espn.com/nfl/story/_/id/49377273/carolina-panthers-training-camp-2026-intel-updates",
  CHI: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  CIN: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  CLE: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  DAL: "https://www.espn.com/nfl/story/_/id/49376535/dallas-cowboys-training-camp-2026-intel-updates",
  DEN: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  DET: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  GB: "https://www.espn.com/nfl/story/_/id/49376941/green-bay-packers-training-camp-2026-intel-updates",
  HOU: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  IND: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  JAX: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  KC: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  LAC: "https://www.espn.com/nfl/story/_/id/49424976/los-angeles-chargers-training-camp-2026-intel-updates",
  LAR: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  LV: "https://www.espn.com/nfl/story/_/id/49425032/las-vegas-raiders-training-camp-2026-intel-updates",
  MIA: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  MIN: "https://www.espn.com/nfl/story/_/id/49376202/minnesota-vikings-training-camp-2026-intel-updates",
  NE: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  NO: "https://www.espn.com/nfl/story/_/id/49424731/new-orleans-saints-training-camp-2026-intel-updates",
  NYG: "https://www.espn.com/nfl/story/_/id/49434181/new-york-giants-training-camp-2026-intel-updates",
  NYJ: "https://www.espn.com/nfl/story/_/id/49419756/new-york-jets-training-camp-2026-intel-updates",
  PHI: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  PIT: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  SEA: "https://www.espn.com/nfl/story/_/id/49427699/seattle-seahawks-training-camp-2026-intel-updates",
  SF: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  TB: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  TEN: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
  WAS: "https://www.espn.com/nfl/story/_/id/49368181/training-camp-2026-latest-news-intel-updates-buzz-all-32-teams",
};

function campDeskContentDir(): string {
  const candidates = [
    path.join(process.cwd(), "../../content/writers/camp-desk-2026"),
    path.join(process.cwd(), "content/writers/camp-desk-2026"),
    path.join(process.cwd(), "../content/writers/camp-desk-2026"),
  ];
  return candidates.find((dir) => existsSync(dir)) ?? candidates[0];
}

function loadCampDeskDayFiles(): CampDeskDayFile[] {
  const dir = campDeskContentDir();
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((name) => /^\d{4}-\d{2}-\d{2}\.json$/.test(name))
    .sort()
    .reverse()
    .flatMap((name) => {
      try {
        const raw = JSON.parse(
          readFileSync(path.join(dir, name), "utf8"),
        ) as CampDeskDayFile;
        if (
          !raw?.desk_date ||
          !raw.league_wrap ||
          !Array.isArray(raw.team_notes)
        ) {
          return [];
        }
        return [raw];
      } catch {
        return [];
      }
    });
}

function loadRotationNext(): string[] {
  const dir = campDeskContentDir();
  const file = path.join(dir, "rotation-queue.json");
  if (!existsSync(file)) return [];
  try {
    const bundled = JSON.parse(readFileSync(file, "utf8")) as {
      next_pulse?: string[];
    };
    return Array.isArray(bundled.next_pulse) ? bundled.next_pulse : [];
  } catch {
    return [];
  }
}

function wireItemInWindow(item: CampNewsItem, now: Date, inCamp: boolean): boolean {
  if (!inCamp) return true;
  if (!item.published) return false;
  const ts = Date.parse(item.published);
  if (!Number.isFinite(ts)) return false;
  return now.getTime() - ts <= 72 * 60 * 60 * 1000;
}

function loadBeatRegistry(): BeatRegistry | null {
  return (beatWritersJson as BeatRegistry) ?? null;
}

function buildBeats(registry: BeatRegistry | null): CampBeatLink[] {
  return NFL_TEAM_DIRECTORY.map((team) => {
    const entry = registry?.teams?.[team.code];
    const writers = entry?.writers ?? [];
    const primary =
      writers.find((w) => w.role === "primary") ?? writers[0] ?? null;
    return {
      team: team.code,
      teamName: team.name,
      division: entry?.division ?? `${team.conference} ${team.division}`,
      kosEdgeWriter: entry?.kos_edge_writer ?? "Desk",
      primaryWriter: primary?.name ?? null,
      primaryOutlet: primary?.outlet ?? null,
      primaryHandle: null,
      espnCampHref: ESPN_TEAM_CAMP_HUBS[team.code] ?? null,
      previewHref: `/pro/nfl/previews/${team.code}`,
    };
  });
}

export async function buildNflCampDesk(opts?: {
  now?: Date;
  team?: string | null;
}): Promise<CampDeskPayload> {
  const now = opts?.now ?? new Date();
  const inCamp = isNflCalendarPreseason(NFL_PRODUCT_SEASON, now);
  const registry = loadBeatRegistry();
  const articles = await fetchEspnNflArticles(50);
  const wire = articles
    .filter(espnItemIsCampRelevant)
    .filter((item) => wireItemInWindow(item, now, inCamp))
    .slice(0, 12);
  const injuryNews = articles
    .filter(espnItemIsInjuryRelevant)
    .filter((item) => wireItemInWindow(item, now, inCamp))
    .slice(0, 8);
  const dayFiles = loadCampDeskDayFiles();
  const allCards = dayFiles.flatMap((file) => cardsFromDayFile(file));
  const shelf = partitionCampDeskShelf(allCards, {
    now,
    team: opts?.team,
    inCamp,
  });
  const kosedgeCards = shelf.live;
  // Preview "camp refs" blocks are not the Camp Desk product surface — skip
  // scanning season-previews so NFT does not pull that tree into this route.
  const writerIntel: CampWriterIntelItem[] = [];
  const beats = buildBeats(registry);
  return {
    generatedAt: now.toISOString(),
    eraLabel: registry?.era ?? "training-camp",
    hubHref: "/pro/nfl/camp",
    kosedgeCards,
    archiveCards: shelf.archive,
    latestDeskDate: shelf.latestDeskDate,
    deskStale: shelf.deskStale,
    sotFlags: collectSotFlags(kosedgeCards),
    previewDelta: collectPreviewDeltas(dayFiles),
    rotationNext: loadRotationNext(),
    wire,
    news: wire,
    injuryNews,
    writerIntel,
    beats,
    writers: WRITER_COVERAGE,
    notes: [
      "Camp Desk hero is KosEdge-dated notes. Beat, official, and multi-source desks are citations — not an X timeline.",
      "Camp/Monday refresh prefers data/writers/nfl-beat-writers.json (research index) over any single outlet. ESPN may be one input, never the branded wire. No X profile links on the product.",
      "During camp, notes older than 72 hours move to Archive. The newest package always stays on the shelf so preseason is never a dead empty state.",
      "Material depth flags queue the existing SoT job. Prose does not publish a new active_run.",
      "Market mentions stay Pass unless a KEI path already supports a tag.",
    ],
    diagnostics: {
      newsCount: wire.length,
      injuryNewsCount: injuryNews.length,
      writerIntelCount: writerIntel.length,
      beatCount: beats.length,
      beatRegistryVersion: registry?.version ?? null,
      kosedgeCardCount: kosedgeCards.length,
      wireCount: wire.length,
    },
  };
}
