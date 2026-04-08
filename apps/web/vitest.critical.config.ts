import { defineConfig, mergeConfig } from "vitest/config";
import base from "./vitest.config";

export default mergeConfig(
  base,
  defineConfig({
    test: {
      include: [
        "__tests__/lib/config/env.test.ts",
        "__tests__/lib/security/rate-limit.test.ts",
        "__tests__/api/auth/register.test.ts",
        "__tests__/lib/edge-board-kei.test.ts",
      ],
      coverage: {
        include: [
          "lib/config/env.ts",
          "lib/security/rate-limit.ts",
          "lib/api/error-handler.ts",
          "app/api/auth/register/route.ts",
          "lib/edge-board-kei.ts",
        ],
        threshold: {
          lines: 70,
          functions: 70,
          branches: 50,
          statements: 70,
        },
      },
    },
  })
);

