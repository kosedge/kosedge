/**
 * Inline-styled boot / recovery shell that remains visible even when the
 * Tailwind CSS chunk fails to load. Used by loading.tsx and global-error.
 */
export const BOOT_SHELL_CSS = `
  html, body { margin: 0; min-height: 100%; background: #070a0f; color: #e9eef5; }
  .kos-boot {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem 1.25rem;
    background:
      radial-gradient(900px 520px at 50% -10%, rgba(245,185,66,0.12), transparent 60%),
      radial-gradient(520px 520px at 0% 20%, rgba(57,255,20,0.08), transparent 55%),
      #070a0f;
    color: #e9eef5;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
  }
  .kos-boot__card {
    width: min(28rem, 100%);
    text-align: center;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(0,0,0,0.35);
    border-radius: 1rem;
    padding: 2rem 1.5rem;
  }
  .kos-boot__brand {
    letter-spacing: 0.08em;
    font-weight: 800;
    text-transform: uppercase;
    font-size: 1.35rem;
    margin: 0 0 0.75rem;
  }
  .kos-boot__brand span:first-child { color: #39ff14; }
  .kos-boot__brand span:last-child { color: #f5b942; }
  .kos-boot__title {
    margin: 0 0 0.5rem;
    font-size: 1.25rem;
    font-weight: 700;
    color: #f5b942;
  }
  .kos-boot__msg {
    margin: 0 0 1.25rem;
    color: rgba(233,238,245,0.78);
    line-height: 1.45;
    font-size: 0.95rem;
  }
  .kos-boot__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 0;
    border-radius: 0.75rem;
    background: #f5b942;
    color: #070a0f;
    font-weight: 700;
    padding: 0.75rem 1.25rem;
    cursor: pointer;
    text-decoration: none;
  }
  .kos-boot__link {
    display: inline-block;
    margin-top: 0.75rem;
    color: rgba(233,238,245,0.7);
    font-size: 0.9rem;
  }
`;

export function BootShellStyles() {
  return <style dangerouslySetInnerHTML={{ __html: BOOT_SHELL_CSS }} />;
}
