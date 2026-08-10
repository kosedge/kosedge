import { renderToStaticMarkup } from "react-dom/server";
import { compileMDX } from "next-mdx-remote/rsc";
import remarkGfm from "remark-gfm";
import { describe, expect, it } from "vitest";
import { useMDXComponents } from "@/mdx-components";

describe("ArticleProseBody GFM tables", () => {
  it("renders pipe tables as HTML table markup", async () => {
    const source = [
      "| Side | Price |",
      "| --- | --- |",
      "| Over 10.5 | +115 |",
      "| Under 10.5 | −140 |",
    ].join("\n");

    const { content } = await compileMDX({
      source,
      components: useMDXComponents({}),
      options: {
        mdxOptions: {
          remarkPlugins: [remarkGfm],
        },
      },
    });

    const html = renderToStaticMarkup(content);

    expect(html).toContain("<table");
    expect(html).toContain("<th");
    expect(html).toContain("<td");
    expect(html).toContain("Over 10.5");
    expect(html).toContain("+115");
    // Raw pipe rows should not remain as a single paragraph blob.
    expect(html).not.toMatch(/\| Side \| Price \|/);
  });
});
