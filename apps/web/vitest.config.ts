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
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: [
        "app/api/**/*.ts",
        "lib/api/**/*.ts",
        "lib/auth/**/*.ts",
        "lib/config/**/*.ts",
        "lib/security/**/*.ts",
        "components/auth/**/*.tsx",
      ],
      exclude: [
        "node_modules/",
        ".next/",
        "**/*.config.{js,ts}",
        "**/types/**",
        "**/*.d.ts",
        "**/vitest.setup.ts",
        "src/generated/**",
      ],
      // Broad suite has a non-zero floor; critical paths have stricter thresholds in vitest.critical.config.ts.
      thresholds: {
        lines: 25,
        functions: 30,
        branches: 20,
        statements: 25,
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
