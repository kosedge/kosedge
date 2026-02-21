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

  // If you ever load remote images, add domains here
  images: {
    remotePatterns: []
  }
};

export default withMDX(nextConfig);