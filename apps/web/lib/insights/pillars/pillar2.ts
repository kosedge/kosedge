import type { InsightSection } from "../types";

export const section1: InsightSection = {
  title: "2.1 EV vs Win Rate (The Difference Between Being Right and Being Profitable)",
  pillarTitle: "PILLAR 2 — What \"Edge\" Actually Means",
  body: [
    "Win rate is what casual bettors talk about because it's intuitive. Expected value (EV) is what professionals talk about because it's real.",
    "A bettor can win 60% of bets and still lose money if they consistently lay bad prices. A bettor can win 52% of bets and make serious money if they're consistently getting plus money that should be closer to even.",
    "EV is the long-run profit expectation of a wager: EV = (True Probability × Payout) − (1 − True Probability) × Risk",
    "That's the core: you're not betting outcomes—you're betting prices.",
    "Kos Edge is built around pricing: we want to know when the market is offering a number that doesn't match reality. That's what edge means. Not \"I feel confident.\" Not \"This team is better.\" Edge is a measurable gap between probability and price.",
    "Win rate is a result. EV is the process.",
  ],
};

export const section2: InsightSection = {
  title: "2.2 Model Price vs Market Price (What We're Actually Selling)",
  pillarTitle: "PILLAR 2 — What \"Edge\" Actually Means",
  body: [
    "Every betting line implies a probability. That's what the market is saying. Your model is what you're saying.",
    "Example: Market implies a team wins 52% of the time. Your model says 57%. That 5% gap is the opportunity—if your model is calibrated and your inputs are strong.",
    "But we don't stop there. We track: whether that gap persists over time, whether it gets corrected by the market, and whether it produces positive EV at bet time.",
    "Kos Edge isn't \"we predict winners.\" Kos Edge is \"we price probability better than the market does—sometimes.\"",
    "That \"sometimes\" is important. It's why we don't sell picks. We sell information that creates better decisions.",
  ],
};

export const section3: InsightSection = {
  title: "2.3 Open vs Close (Why the Market Moves Matters)",
  pillarTitle: "PILLAR 2 — What \"Edge\" Actually Means",
  body: [
    "Open lines are the sportsbook's starting estimate. Closing lines are the market's final consensus after sharp money and information flows in.",
    "Tracking open vs close answers two questions: 1) Did our number beat the market early? 2) Did our number hold up as the market corrected?",
    "People obsess over CLV because it's one of the cleanest \"skill signals\" we can measure. But we don't treat it as religion. We treat it as one part of the feedback loop.",
    "Our core credibility engine is: model vs open, model vs close, realized EV (what price you actually bet).",
    "Because most bettors are not betting 10 minutes after open. They're betting closer to close. So our job is to build a model that holds value even when liquidity increases.",
  ],
};

export const section4: InsightSection = {
  title: "2.4 CLV Matters (But It Isn't the Whole Game)",
  pillarTitle: "PILLAR 2 — What \"Edge\" Actually Means",
  body: [
    "CLV is powerful because it's not luck-based. It measures whether you consistently got better prices than the market finished at.",
    "But CLV isn't the entire truth: some markets are inefficient until close, some move due to injury news, some close numbers aren't \"sharp\" (especially in certain props).",
    "We track CLV because it's diagnostic: Are we seeing the market correctly? Are we early to information? Are we pricing probability better than consensus?",
    "But ultimately, we care about what matters most: expected value at the time the bet is placed.",
    "Kos Edge uses CLV as a tool—not a marketing trick.",
  ],
};
