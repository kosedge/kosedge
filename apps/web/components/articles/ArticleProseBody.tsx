import { MDXRemote } from "next-mdx-remote/rsc";
import { useMDXComponents } from "@/mdx-components";
import { articleProseClasses } from "@/lib/article-prose";

type ArticleProseBodyProps = {
  source: string;
  className?: string;
};

export default function ArticleProseBody({
  source,
  className = "",
}: ArticleProseBodyProps) {
  if (!source.trim()) return null;
  const components = useMDXComponents({});

  return (
    <div className={`${articleProseClasses} ${className}`.trim()}>
      <MDXRemote source={source} components={components} />
    </div>
  );
}
