import path from "path";
import type { NextConfig } from "next";
import createMDX from "@next/mdx";

const withMDX = createMDX({
  extension: /\.mdx?$/,
});

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Standalone causes pnpm monorepo issues on Vercel (missing workspace deps). Omit for Vercel.
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
  pageExtensions: ["ts", "tsx", "mdx"],

  // Monorepo: Turbopack must use repo root so pnpm node_modules and Next.js resolve (scheduler, react-dom, etc.)
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },

  // So Turbopack/Node resolve from apps/web node_modules (pnpm symlinks)
  serverExternalPackages: ["bcryptjs"],

  // Good default hardening
  poweredByHeader: false,

  // nfl-preseason-artifacts.ts / nfl-vegas-benchmark.ts / nfl-clv-benchmark.ts
  // read data/ops/** via dynamic readdirSync/readFileSync (runtime-computed
  // paths, not static imports) so Next's default file-tracing can't detect
  // the dependency and excludes it from the deployed function bundle --
  // this silently broke these pages in production ("No 2026 preseason
  // simulation bundle was found yet") despite the files being committed.
  // Keep heavy monorepo training/raw artifacts out of every serverless NFT.
  // findRepoRoot()-style probes under data/ otherwise pull hundreds of MB.
  outputFileTracingExcludes: {
    "*": [
      // apps/web/data (NCAAB raw odds ~300MB) — NOT repo-root ../../data
      "./data/raw/**/*",
      "./data/processed/**/*",
      "./data/historical-odds/**/*",
      "./data/fantasy/**/*",
      "./src/**/*",
      "./prisma/**/*",
      "./scripts/**/*",
      "../../data/raw/**/*",
      "../../data/processed/**/*",
      "../../data/mlb/**/*",
      "../../data/backups/**/*",
      "../../apps/android-odds-widget/**/*",
      "../../**/.gradle/**/*",
      "./**/playwright-report/**/*",
      "./**/coverage/**/*",
      "./tsconfig.tsbuildinfo",
    ],
    "/pro/nfl/camp": [
      "./data/**/*",
      "../../data/ops/**/*",
      "../../data/fantasy/**/*",
    ],
  },

  outputFileTracingIncludes: {
    "/pro/nfl/projections": ["../../data/ops/**/*"],
    "/pro/nfl/previews": ["../../content/writers/season-previews-2026/**/*"],
    "/pro/nfl/previews/[team]": [
      "../../content/writers/season-previews-2026/**/*",
    ],
    "/pro/nfl/stats": ["../../data/ops/**/*"],
    "/pro/nfl/slate/[date]": ["../../data/ops/**/*"],
    // Camp Desk: beat registry + daily JSON only (no season-previews / data/ops).
    "/pro/nfl/camp": [
      "../../data/writers/**/*",
      "../../content/writers/camp-desk-2026/**/*",
    ],
    "/pro/[sport]/tracking": ["../../data/ops/nfl-clv-benchmark-report.json"],
    "/pro/nfl/injuries": ["../../data/writers/**/*"],
    "/pro/prediction-market": [
      "../../data/ops/**/*",
      "../../content/writers/season-previews-2026/**/*",
    ],
    "/pro/power-ratings/[sport]": ["../../data/ops/**/*"],
    "/pro/clv-tracker": ["../../data/ops/**/*"],
    "/pro/model-transparency": ["../../data/ops/**/*"],
    "/pro/nfl/news": ["../../content/writers/news-breaks-2026/**/*"],
    "/pro/nfl/news/[slug]": ["../../content/writers/news-breaks-2026/**/*"],
    "/pro/desk": ["../../content/writers/desk-2026/**/*"],
    "/pro/desk/[slug]": ["../../content/writers/desk-2026/**/*"],
    // Fantasy desk: depth SoT for colliding abbrevs (Bijan vs Brian Robinson).
    // Static import of lib/fantasy/data also bundles; NFT include covers FS reads.
    "/pro/nfl/fantasy": [
      "./lib/fantasy/data/**/*",
      "../../services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    ],
    "/pro/nfl/fantasy/mock": [
      "./lib/fantasy/data/**/*",
      "../../services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    ],
    "/pro/nfl/fantasy/builder": [
      "./lib/fantasy/data/**/*",
      "../../services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    ],
    "/pro/nfl/fantasy/sleepers": [
      "./lib/fantasy/data/**/*",
      "../../services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    ],
    "/pro/nfl/fantasy/guillotine": [
      "./lib/fantasy/data/**/*",
      "../../services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    ],
    "/pro/nfl/fantasy/player/[playerId]": [
      "./lib/fantasy/data/**/*",
      "../../services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    ],
  },

  async redirects() {
    return [
      {
        // Pipeline stub — live NFL KEI board is fair-lines (do not mint kei_lines_nfl.json).
        source: "/pro/kei-lines/nfl",
        destination: "/pro/nfl/fair-lines",
        permanent: false,
      },
      {
        // Sport-first alias never had a page — permanent hop to the live fair-lines desk.
        // CoS Gap Matrix: /pro/{sport}/kei-lines 404'd all six with no redirect.
        source: "/pro/:sport(nfl|cfb|mlb|nba|nhl|wnba)/kei-lines",
        destination: "/pro/:sport/fair-lines",
        permanent: true,
      },
      {
        // Odds-API / colloquial alias — same CFB fair-lines desk (Alex #5).
        source: "/pro/ncaaf/kei-lines",
        destination: "/pro/cfb/fair-lines",
        permanent: true,
      },
      {
        source: "/pro/ncaaf/fair-lines",
        destination: "/pro/cfb/fair-lines",
        permanent: true,
      },
      {
        // Edge Board Product Center (#4): canonical public decision center is
        // /edge-board/{sport}. Soft page redirects returned 200 + meta refresh —
        // permanent hop so bookmarks / pro aliases share one URL (query preserved).
        source: "/pro/:sport(nfl|cfb|mlb|nba|nhl|wnba|ncaam)/edge-board",
        destination: "/edge-board/:sport",
        permanent: true,
      },
      {
        // Typed alias — same board as /edge-board/nfl.
        source: "/pro/nfl/boards",
        destination: "/edge-board/nfl",
        permanent: true,
      },
      {
        source: "/pro/nfl/odds",
        destination: "/odds/nfl",
        permanent: false,
      },
      {
        source: "/pro/nfl/intel",
        destination: "/pro/nfl/teams",
        permanent: false,
      },
      {
        source: "/pro/nfl/hub",
        destination: "/pro/nfl/overview",
        permanent: false,
      },
      {
        source: "/pro/nfl/players",
        destination: "/pro/nfl/player-previews",
        permanent: false,
      },
      {
        source: "/pro/power-ratings/cfb",
        destination: "/pro/cfb/teams",
        permanent: false,
      },
      {
        source: "/pro/cfb/slate/today",
        destination: "/pro/cfb/slate",
        permanent: false,
      },
      {
        source: "/pro/cfb/slate/:date",
        destination: "/pro/cfb/slate",
        permanent: false,
      },
      // NOTE: Do NOT add a /Brand → /brand redirect. Next/Vercel matchers are
      // case-insensitive, so that redirect infinite-loops and breaks next/image.
      // Both `public/brand` and `public/Brand` are shipped instead.
    ];
  },

  async headers() {
    return [
      {
        // HTML documents must never be served from a long-lived cache across deploys.
        source: "/:path*",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
        ],
      },
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },

  // If you ever load remote images, add domains here
  images: {
    remotePatterns: [],
  },
};

export default withMDX(nextConfig);
