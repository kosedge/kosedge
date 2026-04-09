#!/usr/bin/env node
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

function readAllowlist(path) {
  return new Set(
    readFileSync(path, "utf-8")
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith("#"))
  );
}

function listTrackedPythonUnderWeb() {
  const out = execSync('git ls-files "apps/web/*.py" "apps/web/**/*.py"', {
    encoding: "utf-8",
  });
  return new Set(
    out
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
  );
}

const allowlist = readAllowlist("policies/web-python-allowlist.txt");
const tracked = listTrackedPythonUnderWeb();

const unexpected = [...tracked].filter((f) => !allowlist.has(f)).sort();
const missing = [...allowlist].filter((f) => !tracked.has(f)).sort();

if (unexpected.length === 0 && missing.length === 0) {
  console.log("Python boundary check passed: apps/web Python footprint unchanged.");
  process.exit(0);
}

console.error("Python boundary check failed.");
if (unexpected.length) {
  console.error("\nUnexpected Python files in apps/web:");
  for (const f of unexpected) console.error(`  - ${f}`);
}
if (missing.length) {
  console.error("\nAllowlisted files no longer tracked (update allowlist if intentional):");
  for (const f of missing) console.error(`  - ${f}`);
}
console.error(
  "\nPolicy: new Python ingestion/model code should live under services/ (not apps/web). " +
    "If this is an intentional migration, update policies/web-python-allowlist.txt in the same PR."
);
process.exit(1);

