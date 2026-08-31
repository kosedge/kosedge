import { BootShellStyles } from "@/components/BootShell";

export default function ProLoading() {
  return (
    <>
      <BootShellStyles />
      <div
        className="kos-boot"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <div className="kos-boot__card">
          <p className="kos-boot__brand">
            <span>Kos</span> <span>Edge</span>
          </p>
          <p className="kos-boot__title">Opening Pro desk…</p>
          <p className="kos-boot__msg">Loading research tools…</p>
        </div>
      </div>
    </>
  );
}
