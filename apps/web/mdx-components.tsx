// apps/web/mdx-components.tsx
import type { ComponentProps } from "react";

// MDX components map - avoid mdx/types to prevent build dependency
type MDXComponentsMap = ComponentProps<
  (typeof import("next-mdx-remote/rsc"))["MDXRemote"]
>["components"];

export function useMDXComponents(
  components: MDXComponentsMap = {},
): MDXComponentsMap {
  return {
    ...components,
  };
}
