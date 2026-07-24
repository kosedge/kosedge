import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: [
      "__tests__/lib/config/env.test.ts",
      "__tests__/lib/security/rate-limit.test.ts",
      "__tests__/api/auth/register.test.ts",
      "__tests__/lib/edge-board-kei.test.ts",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: [
        "lib/config/env.ts",
        "lib/security/rate-limit.ts",
        "lib/api/error-handler.ts",
        "app/api/auth/register/route.ts",
        "lib/edge-board-kei.ts",
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 50,
        statements: 70,
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
