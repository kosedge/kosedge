import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";
import { getMdxBySlug, getMdxSlugs } from "@/lib/mdx";
import { useMDXComponents } from "@/mdx-components";

export function generateStaticParams() {
  return getMdxSlugs("insights").map((slug) => ({ slug }));
}

export default function InsightPage({ params }: { params: { slug: string } }) {
  const slugs = getMdxSlugs("insights");
  if (!slugs.includes(params.slug)) return notFound();

  const post = getMdxBySlug("insights", params.slug);

  return (
    <main className="min-h-screen bg-kos-black">
      <article className="mx-auto max-w-3xl px-6 py-14">
        <div className="rounded-2xl border border-kos-border bg-kos-surface/40 p-8">
          <p className="text-sm text-kos-text/60">{post.frontmatter.date}</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-kos-text">
            {post.frontmatter.title}
          </h1>
          {post.frontmatter.description && (
            <p className="mt-4 text-kos-text/80">{post.frontmatter.description}</p>
          )}
        </div>

        <div className="prose prose-invert mt-10 max-w-none">
          <MDXRemote source={post.content} components={useMDXComponents({})} />
        </div>
      </article>
    </main>
  );
}