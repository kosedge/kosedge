import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Kos Edge Analytics",
    template: "%s • Kos Edge Analytics",
  },
  description: "Premium sports handicapping insights built on data. Driven by edge.",
  metadataBase: new URL("https://kosedge.com"),
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
      <body>{children}</body>
    </html>
  );
}