import { notFound, redirect } from "next/navigation";
import { getDoctrineBySlug, getDeskNoteBySlug } from "@/lib/insights/content";

/**
 * Legacy /insights/[slug] permalinks.
 * Canonical routes are /insights/doctrine/[slug] and /insights/notes/[slug].
 */
export default async function LegacyInsightSlugPage({
  params,
}: {
  params: Promise<{ slug: string }> | { slug: string };
}) {
  const resolved =
    params && typeof (params as Promise<unknown>).then === "function"
      ? await (params as Promise<{ slug: string }>)
      : (params as { slug: string });

  const { slug } = resolved;

  // Reserved section paths should never hit this dynamic route, but guard anyway.
  if (slug === "doctrine" || slug === "sports" || slug === "notes") {
    redirect(`/insights/${slug}`);
  }

  const doctrine = getDoctrineBySlug(slug);
  if (doctrine) redirect(`/insights/doctrine/${slug}`);

  const note = getDeskNoteBySlug(slug);
  if (note) redirect(`/insights/notes/${slug}`);

  return notFound();
}
