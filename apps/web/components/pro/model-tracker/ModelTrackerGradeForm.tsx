"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export default function ModelTrackerGradeForm({ pickId }: { pickId: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const fd = new FormData(e.currentTarget);
    try {
      const res = await fetch("/api/model-tracker", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "grade",
          pick_id: pickId,
          home_score: Number(fd.get("home_score")),
          away_score: Number(fd.get("away_score")),
        }),
      });
      const data = (await res.json()) as { error?: string };
      if (!res.ok || data.error) {
        setError(data.error || `Grade failed (${res.status})`);
        return;
      }
      startTransition(() => router.refresh());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Grade failed");
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2">
      <label className="text-[11px] text-kos-text/50">
        H
        <input
          name="home_score"
          type="number"
          required
          min={0}
          className="mt-0.5 w-14 rounded border border-kos-border bg-kos-bg/60 px-1.5 py-1 text-xs"
        />
      </label>
      <label className="text-[11px] text-kos-text/50">
        A
        <input
          name="away_score"
          type="number"
          required
          min={0}
          className="mt-0.5 w-14 rounded border border-kos-border bg-kos-bg/60 px-1.5 py-1 text-xs"
        />
      </label>
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-white/15 px-2 py-1 text-[11px] text-kos-text/80 hover:border-kos-gold/40 disabled:opacity-50"
      >
        {pending ? "…" : "Grade"}
      </button>
      {error ? <span className="text-[11px] text-red-400">{error}</span> : null}
    </form>
  );
}
