"use client";

import { useEffect } from "react";
import { logError } from "@/lib/logger";
import { BootShellStyles } from "@/components/BootShell";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logError(error, {
      digest: error.digest,
      errorBoundary: false,
    });
  }, [error]);

  return (
    <>
      <BootShellStyles />
      <div className="kos-boot">
        <div className="kos-boot__card">
          <p className="kos-boot__brand">
            <span>Kos</span> <span>Edge</span>
          </p>
          <h1 className="kos-boot__title">Something Went Wrong</h1>
          <p className="kos-boot__msg">
            An error occurred while loading this page. Try again or return
            home — content should never disappear into a black void.
          </p>
          <button type="button" className="kos-boot__btn" onClick={reset}>
            Try Again
          </button>
          <div>
            <a className="kos-boot__link" href="/">
              Go Home
            </a>
          </div>
          {process.env.NODE_ENV === "development" && error?.message ? (
            <pre
              style={{
                marginTop: "1.25rem",
                textAlign: "left",
                fontSize: "0.75rem",
                color: "#fca5a5",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {error.message}
            </pre>
          ) : null}
        </div>
      </div>
    </>
  );
}
