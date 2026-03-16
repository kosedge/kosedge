#!/usr/bin/env node
/**
 * Run vitest by resolving it from the package's node_modules.
 * Used so tests work under pnpm when .bin/vitest is not on PATH.
 */
import { spawn } from "child_process";
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const packageRoot = path.resolve(__dirname, "..");

let binPath;
try {
  const pkgPath = require.resolve("vitest/package.json", { paths: [packageRoot] });
  const pkg = require(pkgPath);
  const bin = pkg.bin?.vitest ?? pkg.bin;
  const binFile = typeof bin === "string" ? bin : "vitest.mjs";
  binPath = path.join(path.dirname(pkgPath), binFile);
} catch {
  console.error("vitest not found. Run pnpm install from the repo root.");
  process.exit(1);
}

const args = process.argv.slice(2);
const child = spawn(process.execPath, [binPath, ...args], {
  stdio: "inherit",
  cwd: packageRoot,
});
child.on("exit", (code) => process.exit(code ?? 0));
child.on("error", (err) => {
  console.error(err);
  process.exit(1);
});
