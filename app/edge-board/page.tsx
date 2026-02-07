// app/edge-board/page.tsx
import EdgeBoard from "@/components/EdgeBoard";

export default function EdgeBoardPage() {
  return (
    <main className="min-h-screen bg-[#070A0F] text-gray-100 relative overflow-hidden">
      {/* subtle background (matches homepage vibe) */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-44 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-kos-gold/10 blur-3xl" />
        <div className="absolute top-24 -left-40 h-[520px] w-[520px] rounded-full bg-kos-green/10 blur-3xl" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70" />
      </div>

      <div className="relative z-10">
        <EdgeBoard variant="full" />
      </div>
    </main>
  );
}