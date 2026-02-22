"use client";

import { useEffect } from "react";
import { logError } from "@/lib/logger";
import { ErrorScreen } from "@/components/error/ErrorScreen";

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
    <ErrorScreen
      title="Something Went Wrong"
      message="An error occurred while loading this page."
      secondaryMessage="Please try again or return to the homepage."
      primaryLabel="Try Again"
      onPrimary={reset}
      showDevDetails={process.env.NODE_ENV === "development"}
      error={error}
    />
  );
}
