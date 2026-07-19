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
  outputFileTracingIncludes: {
    "/pro/nfl/projections": ["../../data/ops/**/*"],
    "/pro/clv-tracker": ["../../data/ops/**/*"],
    "/pro/model-transparency": ["../../data/ops/**/*"],
  },

  // If you ever load remote images, add domains here
  images: {
    remotePatterns: [],
  },
};

export default withMDX(nextConfig);
