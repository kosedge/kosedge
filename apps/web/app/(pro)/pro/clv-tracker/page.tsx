import Link from "next/link";
import NflProShell from "@/components/pro/nfl/NflProShell";

/**
 * CLV Tracker (KOS-22 C26 / Riley U02).
 * Public beat-rate / average-CLV customer metrics dark until Signal Ledger exists.
 * CLV Tracker ≠ Signal Ledger — do not rename; honest unavailable state only.
 */
export default function CLVTrackerPage() {
  return (
    <NflProShell
      pageTitle="CLV Tracker"
      pageSubtitle="Closing Line Value accountability. Customer CLV performance metrics unavailable until Signal Ledger."
      actions={
        <Link
          href="/pro/model-transparency"
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
        >
          Model Transparency
        </Link>
      }
    >
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        <p
          className="text-sm text-kos-text/60"
          data-testid="clv-tracker-unavailable"
        >
          Customer CLV performance metrics unavailable until Signal Ledger.
        </p>
      </main>
    </NflProShell>
  );
}
