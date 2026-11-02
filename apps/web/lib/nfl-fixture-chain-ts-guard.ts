/**
 * t5201u P14 — Node/vitest forbidden-call guard for the A→B chain leg.
 * Active only when T5201U_CHAIN_JSON is set. CERT=0. Not a production wrap.
 */
import { createRequire } from "node:module";
import Module from "node:module";

const attempts: string[] = [];

const DB_MODULES = new Set([
  "pg",
  "pg-native",
  "ioredis",
  "redis",
  "@prisma/client",
  "prisma",
  "#prisma",
]);

function isDbModule(id: string): boolean {
  const top = id.startsWith("@") ? id.split("/").slice(0, 2).join("/") : id.split("/")[0];
  return DB_MODULES.has(id) || DB_MODULES.has(top);
}

function note(name: string): never {
  attempts.push(name);
  throw new Error(`FIXTURE TS HARD REFUSE forbidden call ${name}`);
}

export function tsForbiddenCallAttempts(): number {
  return attempts.length;
}

export function tsForbiddenCallNames(): readonly string[] {
  return attempts;
}

export function printTsForbiddenReport(): void {
  const line = `ts_forbidden_call_attempts ${attempts.length}\n`;
  process.stdout.write(line);
}

export function installTsChainGuard(): void {
  const g = globalThis as typeof globalThis & { __t5201u_ts_guard?: boolean };
  if (g.__t5201u_ts_guard) return;
  g.__t5201u_ts_guard = true;

  const nodeRequire = createRequire(import.meta.url);
  const net = nodeRequire("net") as typeof import("node:net");
  const dns = nodeRequire("dns") as typeof import("node:dns");
  const http = nodeRequire("http") as typeof import("node:http");
  const https = nodeRequire("https") as typeof import("node:https");

  globalThis.fetch = ((..._args: Parameters<typeof fetch>) => {
    note("fetch");
  }) as typeof fetch;

  (net as { connect: unknown }).connect = (..._args: unknown[]) => note("net.connect");
  net.Socket.prototype.connect = function (..._args: unknown[]) {
    note("net.Socket.connect");
  } as typeof net.Socket.prototype.connect;

  (dns as { lookup: unknown }).lookup = (..._args: unknown[]) => note("dns.lookup");
  (http as { request: unknown }).request = (..._args: unknown[]) => note("http.request");
  (https as { request: unknown }).request = (..._args: unknown[]) => note("https.request");

  const origLoad = (Module as unknown as { _load?: (...a: unknown[]) => unknown })._load;
  if (typeof origLoad === "function") {
    (Module as unknown as { _load: (...a: unknown[]) => unknown })._load = function (
      request: unknown,
      ...rest: unknown[]
    ) {
      const id = String(request);
      if (isDbModule(id)) note(`import:${id}`);
      return origLoad.call(this, request, ...rest);
    };
  }

  const origCreateRequire = Module.createRequire.bind(Module);
  Module.createRequire = ((filename: string | URL) => {
    const req = origCreateRequire(filename);
    const wrapped = ((id: string) => {
      if (isDbModule(id)) note(`import:${id}`);
      return req(id);
    }) as NodeRequire;
    return Object.assign(wrapped, req);
  }) as typeof Module.createRequire;
}

export function probeTsForbidden(): number {
  const before = attempts.length;
  const nodeRequire = createRequire(import.meta.url);
  const net = nodeRequire("net") as typeof import("node:net");
  const dns = nodeRequire("dns") as typeof import("node:dns");
  const http = nodeRequire("http") as typeof import("node:http");
  const https = nodeRequire("https") as typeof import("node:https");

  const hits: string[] = [];
  const tryCall = (name: string, fn: () => void) => {
    try {
      fn();
    } catch {
      hits.push(name);
    }
  };
  tryCall("fetch", () => {
    void globalThis.fetch("http://203.0.113.1/");
  });
  tryCall("net.connect", () => {
    net.connect({ port: 9, host: "203.0.113.1" });
  });
  tryCall("dns.lookup", () => {
    dns.lookup("example.test", () => undefined);
  });
  tryCall("http.request", () => {
    http.request("http://203.0.113.1/");
  });
  tryCall("https.request", () => {
    https.request("https://203.0.113.1/");
  });
  tryCall("import:pg", () => {
    nodeRequire("pg");
  });
  const gained = attempts.length - before;
  if (hits.length < 2 || gained < 2) {
    throw new Error(
      `ts probe expected fetch/net/dns/http/db attempts, got hits=${hits.length} counted=${gained}`,
    );
  }
  return gained;
}
