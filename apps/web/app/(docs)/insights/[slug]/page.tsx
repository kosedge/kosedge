import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";
import ArticleLayout from "@/components/layout/ArticleLayout";
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
    <ArticleLayout
      title={post.frontmatter.title}
      subtitle={post.frontmatter.description}
    >
      <p className="text-sm text-kos-text/60">{post.frontmatter.date}</p>
      <div className="prose prose-invert mt-10 max-w-none">
        <MDXRemote source={post.content} components={useMDXComponents({})} />
      </div>
    </ArticleLayout>
  );
}