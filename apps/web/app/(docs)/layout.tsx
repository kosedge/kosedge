import SiteHeader from "@/components/layout/SiteHeader";

/**
 * Shared shell for (docs) route group: Insights index and [slug].
 * Provides consistent header and full-bleed background; pages control their own content width.
 */
export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-kos-black">
      <SiteHeader />
      {children}
    </div>
  );
}
