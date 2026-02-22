import type { InsightSection } from "../types";

export const section1: InsightSection = {
  title: "1.1 Parlays Are a Tax on the Uneducated",
  pillarTitle:
    "PILLAR 1 — Why Most Bettors Lose (And It's Not What They Think)",
  body: [
    "Parlays feel like the fastest path to a \"big win,\" which is exactly why sportsbooks push them so hard. The book isn't promoting parlays because they're fun. They're promoting them because parlays increase hold (the sportsbook's expected profit).",
    "Here's the core problem: every additional leg multiplies uncertainty, and the market prices that uncertainty in a way that usually benefits the house.",
    "If you're a legitimately strong bettor who wins 55% of straight bets (which is rare), the probability of hitting a 3-leg parlay is: 0.55 × 0.55 × 0.55 = 0.166 (16.6%).",
    "Most bettors don't realize what's happening psychologically:",
    [
      "You're stacking variance (more ways to lose)",
      "You're trading edge for dopamine",
      'You\'re confusing "smart" with "complicated"',
    ],
    'Parlays also hide the real pricing. With singles, you can identify a mispriced line. With parlays, you\'re often accepting a payout that "looks fair" without checking whether the implied probability is actually accurate.',
    'This is why Kos Edge is built around numbers, not narrative. Our product is not "what to bet." It\'s "what price is wrong." Parlays make it harder to stay disciplined and easier to rationalize bad pricing.',
    "If you want to parlay for entertainment, fine—call it what it is. But if your goal is consistent profitability, parlays are usually a drag on your long-term expected value.",
  ],
};

export const section2: InsightSection = {
  title: '1.2 The -600 Trap (Why "Safe" Bets Aren\'t Safe)',
  pillarTitle:
    "PILLAR 1 — Why Most Bettors Lose (And It's Not What They Think)",
  body: [
    "A -600 line implies the outcome happens about 85.7% of the time. That sounds nearly guaranteed—until you realize the entire bet is about one thing: whether the price is fair.",
    "If the true probability is 83% and the book prices it as 85.7%, you're making a negative EV bet—even if it wins most nights.",
    "The trap is emotional:",
    ["It feels safe", "It reduces short-term pain", 'It gives you "momentum"'],
    "But bankroll math doesn't care about comfort. If you risk $600 to win $100, a single loss wipes out six wins. That's why books love letting casual bettors \"build bankrolls\" with heavy favorites—because eventually a few upsets erase weeks of perceived progress.",
    "Kos Edge exists to break this mindset. We don't measure bets by how often they win. We measure them by expected value at the price you paid.",
    'The long game is not "avoid losing." The long game is "pay less than the true cost of probability."',
    "That's how professionals think. They don't chase safety. They chase mispricing.",
  ],
};

export const section3: InsightSection = {
  title: "1.3 Emotional Chasing (The Silent Bankroll Killer)",
  pillarTitle:
    "PILLAR 1 — Why Most Bettors Lose (And It's Not What They Think)",
  body: [
    "Most bettors don't lose because they're dumb. They lose because they're human.",
    "After a loss, the brain wants resolution. It wants the pain to stop. That creates the most expensive behavior in betting: chasing.",
    "Chasing isn't just \"betting more.\" It's a package deal:",
    [
      "Bet size increases",
      "Selectivity disappears",
      "You start betting things you wouldn't touch earlier",
      "You shorten your decision window (bad signal processing)",
      "You override your own rules",
    ],
    "The most dangerous part: chasing makes you feel like you're \"taking control.\" But you're not controlling outcomes—you're increasing volatility at the worst time.",
    "That's why we're obsessive about discipline philosophy at Kos Edge. If you don't have a system, your emotions become your system. And emotions are not calibrated to probability.",
    "A disciplined bettor can survive variance. A chasing bettor eventually creates variance so large no edge can overcome it.",
    "That's not a moral statement. It's a math statement.",
  ],
};

export const section4: InsightSection = {
  title: '1.4 No Threshold Discipline (Why "Close Enough" Is How You Go Broke)',
  pillarTitle:
    "PILLAR 1 — Why Most Bettors Lose (And It's Not What They Think)",
  body: [
    "Edge isn't a vibe. Edge is a measurable difference between: what the market implies, and what you believe is true.",
    'The problem is most bettors don\'t have a threshold. They bet when something "looks good," which usually means: recency bias, narrative bias, or "I\'ve been watching this team."',
    "A threshold is what turns betting into a business process: If edge ≥ X%, you act. If edge < X%, you pass.",
    "That sounds simple, but it's everything. Because the moment you allow exceptions, you remove the one advantage you actually control: selection discipline.",
    "Kos Edge is built on the idea that we make fewer bets than the average bettor—because we're filtering for price mistakes that clear a standard. This is how sharp betting actually works: you don't need to bet a lot. You need to bet well.",
  ],
};
