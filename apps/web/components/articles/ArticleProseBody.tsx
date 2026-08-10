import { MDXRemote } from "next-mdx-remote/rsc";
import remarkGfm from "remark-gfm";
import { useMDXComponents } from "@/mdx-components";
import { articleProseClasses } from "@/lib/article-prose";

type ArticleProseBodyProps = {
  source: string;
  className?: string;
};

const mdxOptions = {
  mdxOptions: {
    remarkPlugins: [remarkGfm],
  },
};

export default function ArticleProseBody({
  source,
  className = "",
}: ArticleProseBodyProps) {
  const components = useMDXComponents({});
  if (!source.trim()) return null;

  return (
    <div className={`${articleProseClasses} ${className}`.trim()}>
      <MDXRemote source={source} components={components} options={mdxOptions} />
    </div>
  );
}
