import type { ReactNode } from "react";

type Tone = "sky" | "amber" | "neutral";

const TONE: Record<Tone, string> = {
  sky: "border-sky-400/30 bg-sky-400/10 text-sky-100",
  amber: "border-amber-400/30 bg-amber-400/10 text-amber-100",
  neutral: "border-white/15 bg-white/5 text-kos-text/75",
};

const TITLE: Record<Tone, string> = {
  sky: "text-sky-50",
  amber: "text-amber-50",
  neutral: "text-kos-text",
};

/** Clear, honest empty / preseason status — not a “broken” placeholder. */
export function HonestStatusBanner({
  title,
  children,
  tone = "sky",
}: {
  title: string;
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <section className={`rounded-2xl border p-4 text-sm ${TONE[tone]}`}>
      <p className={`font-semibold ${TITLE[tone]}`}>{title}</p>
      <div className="mt-1 opacity-90">{children}</div>
    </section>
  );
}
