import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "dist/**",
    "coverage/**",
    "node_modules/**",
    "next-env.d.ts",
    "public/**",
    "prisma/**",
    "src/generated/**",
    "scripts/**",
    "**/*.wasm",
  ]),
  {
    rules: {
      // Existing codebase uses `any` in several API/test seams; keep as warnings
      // so PR Checks stay green while we tighten types incrementally.
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
    },
  },
  {
    files: ["mdx-components.tsx"],
    rules: {
      // MDX component map uses a conditional pattern Next's MDX helper expects.
      "react-hooks/rules-of-hooks": "off",
    },
  },
]);

export default eslintConfig;
