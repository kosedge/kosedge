"use client";

import { useEffect } from "react";

const RELOAD_KEY = "kosedge:chunk-reload";
const RELOAD_WINDOW_MS = 30_000;

function isChunkLoadFailure(message: string, name?: string, filename?: string): boolean {
  const hay = `${name ?? ""} ${message} ${filename ?? ""}`;
  return (
    /ChunkLoadError/i.test(hay) ||
    /Loading chunk [\w-]+ failed/i.test(hay) ||
    /Failed to fetch dynamically imported module/i.test(hay) ||
    /Importing a module script failed/i.test(hay) ||
    /error loading dynamically imported module/i.test(hay) ||
    (/_next\/static\/chunks\//i.test(hay) && /failed|error|404/i.test(hay))
  );
}

function reloadOnceForNewDeployment(): boolean {
  try {
    const raw = sessionStorage.getItem(RELOAD_KEY);
    const last = raw ? Number(raw) : 0;
    const now = Date.now();
    if (last && now - last < RELOAD_WINDOW_MS) {
      return false;
    }
    sessionStorage.setItem(RELOAD_KEY, String(now));
  } catch {
    // sessionStorage unavailable — still attempt a single reload
  }
  window.location.reload();
  return true;
}

/**
 * Recovers from stale JS/CSS chunks after a rapid Vercel redeploy.
 * Without this, old tabs hit missing `/_next/static/chunks/*` hashes and
 * leave the dark-theme shell as a blank black screen.
 */
export function DeploymentRecovery() {
  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      const msg = event.message || String(event.error || "");
      const name = event.error instanceof Error ? event.error.name : undefined;
      if (isChunkLoadFailure(msg, name, event.filename)) {
        event.preventDefault();
        reloadOnceForNewDeployment();
      }
    };

    const onRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const msg =
        reason instanceof Error
          ? `${reason.name} ${reason.message}`
          : String(reason ?? "");
      if (isChunkLoadFailure(msg)) {
        event.preventDefault();
        reloadOnceForNewDeployment();
      }
    };

    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);

  return null;
}
