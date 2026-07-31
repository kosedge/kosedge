"use client";

import { useEffect } from "react";
import { logError } from "@/lib/logger";
import { BOOT_SHELL_CSS } from "@/components/BootShell";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logError(error, {
      digest: error.digest,
      globalError: true,
    });
  }, [error]);

  return (
    <html lang="en">
      <head>
        <style dangerouslySetInnerHTML={{ __html: BOOT_SHELL_CSS }} />
      </head>
      <body>
        <div className="kos-boot">
          <div className="kos-boot__card">
            <p className="kos-boot__brand">
              <span>Kos</span> <span>Edge</span>
            </p>
            <h1 className="kos-boot__title">Application Error</h1>
            <p className="kos-boot__msg">
              A critical error occurred. Reload to pick up the latest
              deployment — never leave this as a blank black screen.
            </p>
            <button type="button" className="kos-boot__btn" onClick={reset}>
              Reload Application
            </button>
            <div>
              <a className="kos-boot__link" href="/">
                Go Home
              </a>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
