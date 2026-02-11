import SiteHeader from "@/components/SiteHeader";
import Link from "next/link";

export default function MethodologyPage() {
  return (
    <main className="min-h-screen bg-[#070A0F] text-[#E9EEF5]">
      <SiteHeader />
      <section className="mx-auto max-w-4xl px-6 pt-10 pb-20">
        <h1 className="text-4xl font-extrabold">
          Methodology: <span className="text-[#F5B942]">Process Over Noise</span>
        </h1>
        <p className="mt-4 text-white/70">
          Best-line shopping, disciplined thresholds, and long-term thinking.
        </p>
        <div className="mt-8">
          <Link
            href="/insights"
            className="inline-flex rounded-xl bg-[#F5B942] px-5 py-3 text-black font-semibold shadow"
          >
            Read Insights
          </Link>
        </div>
      </section>
    </main>
  );
}