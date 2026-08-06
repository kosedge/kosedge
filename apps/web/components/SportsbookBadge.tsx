import { getSportsbook } from "@/lib/sportsbooks";

export default function SportsbookBadge({
  book,
  compact = false,
}: {
  book?: string | null;
  compact?: boolean;
}) {
  const meta = getSportsbook(book);
  if (!meta) {
    if (!book) return null;
    return (
      <span
        className={`inline-flex items-center rounded border border-white/15 bg-white/5 font-semibold text-gray-300 ${
          compact ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-0.5 text-[10px]"
        }`}
        title={book}
      >
        {book}
      </span>
    );
  }

  const chip = (
    <span
      className={`inline-flex items-center gap-1 rounded border font-semibold ${
        meta.chipClass
      } ${compact ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-0.5 text-[10px]"} ${
        meta.homepage ? "transition hover:brightness-125" : ""
      }`}
    >
      <span
        className={`inline-flex items-center justify-center rounded-sm bg-black/35 font-bebas tracking-wide ${
          compact
            ? "h-3.5 min-w-3.5 px-0.5 text-[9px]"
            : "h-4 min-w-4 px-1 text-[10px]"
        }`}
        aria-hidden
      >
        {meta.short}
      </span>
      {!compact ? <span className="hidden sm:inline">{meta.name}</span> : null}
    </span>
  );

  if (!meta.homepage) {
    return (
      <span title={`${meta.name} consensus`} className="inline-flex">
        {chip}
      </span>
    );
  }

  const external = meta.homepage.startsWith("http");
  return (
    <a
      href={meta.homepage}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      title={
        meta.key === "keinfl"
          ? "KEINFL provisional line (books not posted yet)"
          : `${meta.name} — best price · opens homepage`
      }
      className="inline-flex"
    >
      {chip}
    </a>
  );
}
