// apps/web/components/error/ErrorBoundary.tsx
"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { logError } from "@/lib/logger";
import { BootShellStyles } from "@/components/BootShell";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logError(error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
    });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

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
                We encountered an unexpected error. Reload to recover — do not
                sit on a blank black screen.
              </p>
              <button
                type="button"
                className="kos-boot__btn"
                onClick={() => window.location.reload()}
              >
                Reload Page
              </button>
              <div>
                <a className="kos-boot__link" href="/">
                  Go Home
                </a>
              </div>
              {process.env.NODE_ENV === "development" && this.state.error ? (
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
                  {this.state.error.toString()}
                  {this.state.error.stack
                    ? `\n\n${this.state.error.stack}`
                    : ""}
                </pre>
              ) : null}
            </div>
          </div>
        </>
      );
    }

    return this.props.children;
  }
}
