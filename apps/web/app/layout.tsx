import "./globals.css";
import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Providers } from "./providers";
import { ErrorBoundary } from "@/components/error/ErrorBoundary";
import { DeploymentRecovery } from "@/components/DeploymentRecovery";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: {
    default: "Kos Edge Analytics",
    template: "%s • Kos Edge Analytics",
  },
  description:
    "Premium sports handicapping insights built on data. Driven by edge.",
  metadataBase: new URL("https://www.kosedge.com"),
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={sans.variable} suppressHydrationWarning>
      <body
        className="overflow-x-hidden"
        style={{ backgroundColor: "#070a0f", color: "#e9eef5" }}
      >
        <noscript>
          <div
            style={{
              minHeight: "100vh",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "2rem",
              background: "#070a0f",
              color: "#e9eef5",
              fontFamily: "system-ui, sans-serif",
              textAlign: "center",
            }}
          >
            <div>
              <strong style={{ color: "#f5b942" }}>Kos Edge Analytics</strong>
              <p>JavaScript is required to use the interactive desk.</p>
            </div>
          </div>
        </noscript>
        <DeploymentRecovery />
        <ErrorBoundary>
          <Providers>{children}</Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
