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
    h2: ({ children, ...props }) => (
      <h2
        className="mt-10 mb-4 text-xl font-semibold tracking-tight text-kos-text sm:text-[1.375rem]"
        {...props}
      >
        {children}
      </h2>
    ),
    h3: ({ children, ...props }) => (
      <h3
        className="mt-8 mb-3 text-lg font-semibold tracking-tight text-kos-text"
        {...props}
      >
        {children}
      </h3>
    ),
    p: ({ children, ...props }) => (
      <p
        className="my-4 text-[0.9375rem] leading-[1.75] text-kos-text/90 sm:text-base"
        {...props}
      >
        {children}
      </p>
    ),
    ul: ({ children, ...props }) => (
      <ul className="my-4 list-none space-y-2 pl-0" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol
        className="my-4 list-decimal space-y-2 pl-5 text-kos-text/90"
        {...props}
      >
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => (
      <li
        className="relative pl-5 text-[0.9375rem] leading-relaxed text-kos-text/90 before:absolute before:left-0 before:top-[0.6em] before:h-1.5 before:w-1.5 before:rounded-full before:bg-kos-gold/80 sm:text-base"
        {...props}
      >
        {children}
      </li>
    ),
    strong: ({ children, ...props }) => (
      <strong className="font-semibold text-kos-text" {...props}>
        {children}
      </strong>
    ),
    a: ({ children, href, ...props }) => (
      <a
        href={href}
        className="text-kos-gold underline decoration-kos-gold/40 underline-offset-2 hover:text-kos-gold/90"
        {...props}
      >
        {children}
      </a>
    ),
    blockquote: ({ children, ...props }) => (
      <blockquote
        className="my-6 border-l-2 border-kos-gold/35 pl-4 text-kos-text/85 italic"
        {...props}
      >
        {children}
      </blockquote>
    ),
    table: ({ children, ...props }) => (
      <div className="my-6 overflow-x-auto rounded-xl border border-white/10">
        <table
          className="w-full min-w-[18rem] border-collapse text-left text-sm"
          {...props}
        >
          {children}
        </table>
      </div>
    ),
    thead: ({ children, ...props }) => (
      <thead className="bg-white/5 text-kos-text" {...props}>
        {children}
      </thead>
    ),
    tbody: ({ children, ...props }) => (
      <tbody className="divide-y divide-white/10" {...props}>
        {children}
      </tbody>
    ),
    tr: ({ children, ...props }) => (
      <tr className="border-b border-white/10 last:border-b-0" {...props}>
        {children}
      </tr>
    ),
    th: ({ children, ...props }) => (
      <th
        className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-kos-gold/90 sm:px-4"
        {...props}
      >
        {children}
      </th>
    ),
    td: ({ children, ...props }) => (
      <td
        className="px-3 py-2.5 align-top text-[0.9375rem] leading-relaxed text-kos-text/90 sm:px-4 sm:text-base"
        {...props}
      >
        {children}
      </td>
    ),
    ...components,
  };
}
