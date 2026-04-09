// apps/web/vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    exclude: [
      "node_modules",
      ".next",
      "dist",
      "build",
      "e2e/**",
      "__tests__/lib/auth/pro.test.ts",
      "__tests__/components/auth/UserMenu.test.tsx",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: [
        "node_modules/",
        ".next/",
        "**/*.config.{js,ts}",
        "**/types/**",
        "**/*.d.ts",
        "**/vitest.setup.ts",
        "src/generated/**",
      ],
      // Keep low in broad suite; strict thresholds are enforced in vitest.critical.config.ts
      thresholds: {
        lines: 0,
        functions: 0,
        branches: 0,
        statements: 0,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./"),
      "#prisma": path.resolve(__dirname, "./src/generated/prisma"),
    },
  },
});
