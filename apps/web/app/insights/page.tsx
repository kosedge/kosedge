import Link from "next/link";
import { getAllMdx } from "@/lib/mdx";

export default function InsightsPage() {
  const posts = getAllMdx("insights");

  return (
    <main className="min-h-screen bg-kos-black">
      <div className="mx-auto max-w-4xl px-6 py-14">
        <h1 className="text-4xl font-semibold tracking-tight text-kos-text">
          Insights
        </h1>

        <p className="mt-3 text-kos-text/80">
          Premium-grade sports analytics, released consistently.
        </p>

        <div className="mt-10 space-y-6">
          {posts.map((p) => (
            <Link
              key={p.slug}
              href={`/insights/${p.slug}`}
              className="block rounded-xl border border-kos-border bg-kos-surface/40 p-6 hover:border-kos-gold/40"
            >
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-xl font-semibold text-kos-text">
                  {p.frontmatter.title}
                </h2>
                <span className="text-sm text-kos-text/60">
                  {p.frontmatter.date}
                </span>
              </div>

              {p.frontmatter.description && (
                <p className="mt-2 text-kos-text/80">
                  {p.frontmatter.description}
                </p>
              )}
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}