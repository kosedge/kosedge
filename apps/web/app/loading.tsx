import { BootShellStyles } from "@/components/BootShell";

export default function Loading() {
  return (
    <>
      <BootShellStyles />
      <div className="kos-boot" role="status" aria-live="polite" aria-busy="true">
        <div className="kos-boot__card">
          <p className="kos-boot__brand">
            <span>Kos</span> <span>Edge</span>
          </p>
          <p className="kos-boot__title">Loading desk…</p>
          <p className="kos-boot__msg">
            Pulling the latest board. This should only take a moment.
          </p>
        </div>
      </div>
    </>
  );
}
