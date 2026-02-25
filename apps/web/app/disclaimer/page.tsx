import SiteHeader from "@/components/layout/SiteHeader";

export default function DisclaimerPage() {
  return (
    <main className="min-h-screen bg-[#070A0F] text-[#E9EEF5]">
      <SiteHeader />
      <section className="mx-auto max-w-4xl px-6 pt-10 pb-20">
        <h1 className="text-4xl font-extrabold">Disclaimer</h1>
        <div className="mt-6 space-y-4 text-white/70">
          <p>
            Kos Edge Analytics is for entertainment and informational purposes only.
          </p>
          <p>
            Betting involves risk. Only wager what you can afford to lose.
          </p>
          <p>
            Nothing on this site is financial, legal, or betting advice. You are responsible for your own decisions and for complying with the laws where you live. In many jurisdictions you must be 21 or older to gamble.
          </p>
          <p>
            We do not guarantee any results. Past performance does not guarantee future outcomes. Use this platform at your own risk.
          </p>
        </div>
      </section>
    </main>
  );
}