"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

type Props = {
  defaultSport?: string;
  defaultWeek?: number;
  defaultSeason?: number;
};

export default function ModelTrackerLogForm({
  defaultSport = "cfb",
  defaultWeek = 0,
  defaultSeason = 2026,
}: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [okMsg, setOkMsg] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setOkMsg(null);
    const fd = new FormData(e.currentTarget);
    const payload = {
      action: "log",
      sport: String(fd.get("sport") || defaultSport),
      season: Number(fd.get("season") || defaultSeason),
      week: Number(fd.get("week") || defaultWeek),
      home_team: String(fd.get("home_team") || "").trim().toUpperCase(),
      away_team: String(fd.get("away_team") || "").trim().toUpperCase(),
      market_type: String(fd.get("market_type") || "spread"),
      side: String(fd.get("side") || "").trim().toLowerCase(),
      tag: String(fd.get("tag") || "PLAY"),
      line_at_publish: fd.get("line_at_publish")
        ? Number(fd.get("line_at_publish"))
        : undefined,
      edge_pts: fd.get("edge_pts") ? Number(fd.get("edge_pts")) : undefined,
      game_id: String(fd.get("game_id") || "") || undefined,
      engine_version: String(fd.get("engine_version") || "") || undefined,
      notes: String(fd.get("notes") || "") || undefined,
    };
    try {
      const res = await fetch("/api/model-tracker", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = (await res.json()) as { error?: string; pick?: { id?: string; tag?: string; units?: number } };
      if (!res.ok || data.error) {
        setError(data.error || `Request failed (${res.status})`);
        return;
      }
      setOkMsg(
        `Logged ${data.pick?.tag} · ${data.pick?.units ?? "?"}u · id ${data.pick?.id?.slice(0, 8)}…`,
      );
      startTransition(() => router.refresh());
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  const field =
    "mt-1 w-full rounded-lg border border-kos-border bg-kos-bg/60 px-3 py-2 text-sm text-kos-text outline-none focus:border-kos-gold/50";

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs text-kos-text/60">
          Sport
          <select name="sport" defaultValue={defaultSport} className={field}>
            <option value="cfb">CFB</option>
            <option value="nfl">NFL</option>
            <option value="nba">NBA</option>
            <option value="mlb">MLB</option>
            <option value="wnba">WNBA</option>
          </select>
        </label>
        <label className="text-xs text-kos-text/60">
          Tag
          <select name="tag" defaultValue="PLAY" className={field}>
            <option value="PLAY">PLAY (1 unit)</option>
            <option value="LEAN">LEAN (0 units)</option>
          </select>
        </label>
        <label className="text-xs text-kos-text/60">
          Season
          <input
            name="season"
            type="number"
            defaultValue={defaultSeason}
            className={field}
          />
        </label>
        <label className="text-xs text-kos-text/60">
          Week
          <input
            name="week"
            type="number"
            defaultValue={defaultWeek}
            className={field}
          />
        </label>
        <label className="text-xs text-kos-text/60">
          Away
          <input name="away_team" required placeholder="UNC" className={field} />
        </label>
        <label className="text-xs text-kos-text/60">
          Home
          <input name="home_team" required placeholder="TCU" className={field} />
        </label>
        <label className="text-xs text-kos-text/60">
          Market
          <select name="market_type" defaultValue="spread" className={field}>
            <option value="spread">Spread</option>
            <option value="total">Total</option>
            <option value="moneyline">Moneyline</option>
          </select>
        </label>
        <label className="text-xs text-kos-text/60">
          Side
          <select name="side" defaultValue="home" className={field}>
            <option value="home">Home</option>
            <option value="away">Away</option>
            <option value="over">Over</option>
            <option value="under">Under</option>
          </select>
        </label>
        <label className="text-xs text-kos-text/60">
          Line at publish
          <input
            name="line_at_publish"
            type="number"
            step="0.5"
            placeholder="-3.5"
            className={field}
          />
        </label>
        <label className="text-xs text-kos-text/60">
          Edge pts
          <input name="edge_pts" type="number" step="0.1" className={field} />
        </label>
        <label className="text-xs text-kos-text/60">
          Game id
          <input name="game_id" placeholder="401856766" className={field} />
        </label>
        <label className="text-xs text-kos-text/60">
          Engine version
          <input
            name="engine_version"
            placeholder="cfb-season-engine-…"
            className={field}
          />
        </label>
      </div>
      <label className="block text-xs text-kos-text/60">
        Notes
        <input name="notes" className={field} />
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-medium text-kos-gold hover:bg-kos-gold/25 disabled:opacity-50"
        >
          {pending ? "Logging…" : "Log pick"}
        </button>
        <p className="text-xs text-kos-text/50">
          PLAY = 1u · LEAN = 0u · Internal desk only — not public props chrome
        </p>
      </div>
      {error ? (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      ) : null}
      {okMsg ? <p className="text-sm text-edge-green">{okMsg}</p> : null}
    </form>
  );
}
