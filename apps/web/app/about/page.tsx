import SiteHeader from "@/components/layout/SiteHeader";

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-[#070A0F] text-[#E9EEF5]">
      <SiteHeader />
      <section className="mx-auto max-w-4xl px-6 pt-10 pb-20">
        <h1 className="text-4xl font-extrabold">
          About <span className="text-[#F5B942]">Kos Edge</span>
        </h1>
        <p className="mt-4 text-white/70">
          Kos Edge Analytics is built on disciplined process, not hype.
        </p>
      </section>
    </main>
  );
}