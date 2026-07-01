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

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function pythonScriptViolations() {
  const violations = [];
  const webPkg = readJson("apps/web/package.json");
  for (const [name, cmd] of Object.entries(webPkg.scripts || {})) {
    if (/\bpython(?:\d+)?\b|\bpip\b|\.py\b/i.test(String(cmd))) {
      violations.push(`apps/web/package.json#scripts.${name} -> ${cmd}`);
    }
  }

  const rootPkg = readJson("package.json");
  for (const [name, cmd] of Object.entries(rootPkg.scripts || {})) {
    if (/apps\/web\/.*\.py\b|cd\s+apps\/web\b.*\bpython\b/i.test(String(cmd))) {
      violations.push(`package.json#scripts.${name} -> ${cmd}`);
    }
  }
  return violations;
}

const allowlist = readAllowlist("policies/web-python-allowlist.txt");
const tracked = listTrackedPythonUnderWeb();
const scriptViolations = pythonScriptViolations();

const unexpected = [...tracked].filter((f) => !allowlist.has(f)).sort();
const missing = [...allowlist].filter((f) => !tracked.has(f)).sort();

if (unexpected.length === 0 && missing.length === 0 && scriptViolations.length === 0) {
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
if (scriptViolations.length) {
  console.error("\nPython execution is not allowed in apps/web package scripts:");
  for (const v of scriptViolations) console.error(`  - ${v}`);
}
console.error(
  "\nPolicy: Python ingestion/model execution belongs under services/ (not apps/web). " +
    "If this is an intentional migration step, update policies/web-python-allowlist.txt and boundary scripts in the same PR."
);
process.exit(1);

