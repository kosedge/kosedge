"use client";

import { useEffect } from "react";
import { logError } from "@/lib/logger";
import { ErrorScreen } from "@/components/error/ErrorScreen";

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
    <html>
      <body>
        <ErrorScreen
          title="Application Error"
          message="A critical error occurred. The application needs to reload."
          secondaryMessage="Our team has been notified and is working on a fix."
          primaryLabel="Reload Application"
          onPrimary={reset}
          error={error}
        />
      </body>
    </html>
  );
}
