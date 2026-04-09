import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    ".venv/**",
    "out/**",
    "build/**",
    "dist/**",
    "coverage/**",
    "playwright-report/**",
    "test-results/**",
    "node_modules/**",
    "next-env.d.ts",
    "public/**",
    "prisma/**",
    "src/generated/**",
  ]),
  {
    files: ["**/__tests__/**", "**/*.test.{ts,tsx}", "**/*.spec.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
]);
