"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useTransition, type ReactNode } from "react";

/**
 * Instant-apply filter controls — updates URL search params on change.
 * Replaces "Apply Filters" submit forms across NFL Pro desks.
 */
export function InstantFilterBar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={
        className ??
        "sticky top-[var(--kos-pro-header-h,7.5rem)] z-20 rounded-2xl border border-white/10 bg-black/75 p-4 shadow-xl backdrop-blur-xl"
      }
    >
      {children}
    </div>
  );
}

export function useInstantFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();

  function setParam(key: string, value: string | null | undefined) {
    const next = new URLSearchParams(searchParams.toString());
    if (value == null || value === "") next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    startTransition(() => {
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    });
  }

  function setParams(updates: Record<string, string | null | undefined>) {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value == null || value === "") next.delete(key);
      else next.set(key, value);
    }
    const qs = next.toString();
    startTransition(() => {
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    });
  }

  return { searchParams, setParam, setParams, pending };
}

export function InstantSelect({
  name,
  label,
  value,
  options,
  onChange,
  pending,
}: {
  name: string;
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
  pending?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-kos-text/70">
      {label}
      <select
        name={name}
        value={value}
        disabled={pending}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50 disabled:opacity-60"
      >
        {options.map((opt) => (
          <option key={opt.value || "__all"} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function InstantTextInput({
  name,
  label,
  value,
  placeholder,
  onCommit,
  pending,
}: {
  name: string;
  label: string;
  value: string;
  placeholder?: string;
  onCommit: (value: string) => void;
  pending?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-kos-text/70">
      {label}
      <input
        type="search"
        name={name}
        defaultValue={value}
        placeholder={placeholder}
        disabled={pending}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onCommit((e.target as HTMLInputElement).value);
          }
        }}
        onBlur={(e) => onCommit(e.target.value)}
        className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50 disabled:opacity-60"
      />
    </label>
  );
}
