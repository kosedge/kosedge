"use client";

import type { FormEvent, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

/** GET form that applies filters instantly on change (no Apply button). */
export default function AutoSubmitForm({
  action,
  children,
  className,
}: {
  action: string;
  children: ReactNode;
  className?: string;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function apply(form: HTMLFormElement) {
    const data = new FormData(form);
    const params = new URLSearchParams();
    for (const [key, value] of data.entries()) {
      const v = String(value).trim();
      if (v) params.set(key, v);
    }
    const qs = params.toString();
    startTransition(() => {
      router.replace(qs ? `${action}?${qs}` : action, { scroll: false });
    });
  }

  return (
    <form
      action={action}
      className={className}
      data-pending={pending ? "1" : "0"}
      onChange={(e: FormEvent<HTMLFormElement>) => {
        apply(e.currentTarget);
      }}
      onSubmit={(e) => {
        e.preventDefault();
        apply(e.currentTarget);
      }}
    >
      {children}
      {pending ? (
        <p className="text-[11px] text-kos-text/45 md:col-span-full">
          Updating…
        </p>
      ) : null}
    </form>
  );
}
