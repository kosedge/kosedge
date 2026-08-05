import type { ReactNode } from "react";
import { articleShellClasses } from "@/lib/article-prose";

type ArticleSectionProps = {
  label: string;
  title?: string;
  children: ReactNode;
  id?: string;
};

export default function ArticleSection({
  label,
  title,
  children,
  id,
}: ArticleSectionProps) {
  return (
    <section id={id} className="scroll-mt-28">
      <p className={articleShellClasses.sectionTitle}>{label}</p>
      {title ? (
        <h2 className={articleShellClasses.sectionHeading}>{title}</h2>
      ) : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}
