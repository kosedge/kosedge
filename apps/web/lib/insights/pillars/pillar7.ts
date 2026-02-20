import type { InsightSection } from "../types";

export const section1: InsightSection = {
  title: "7.1 Pitch-Level Modeling (The Real Unit of Baseball)",
  pillarTitle: "PILLAR 7 — Deep Dive: How the MLB Simulation Works (Framework Only)",
  body: [
    "Baseball is not a \"team sport\" in the way basketball is. The atomic unit is pitch → outcome.",
    "At pitch-level, we can model: pitch type distribution, count leverage, location tendencies, batter swing/whiff profiles, contact quality distributions (EV, LA).",
    "This is how you get to true props and true totals—not guesswork.",
  ],
};

export const section2: InsightSection = {
  title: "7.2 Batter vs Pitcher Isn't Simple (But It's Modelable)",
  pillarTitle: "PILLAR 7 — Deep Dive: How the MLB Simulation Works (Framework Only)",
  body: [
    "The matchup is real, but naive \"BvP\" is mostly noise.",
    "The better approach is: batter profile vs pitch mix, batter zone discipline vs pitcher command, whiff rate vs K% induced, barrel probability vs allowed EV/LA.",
    "That becomes a probability engine, not a narrative.",
  ],
};

export const section3: InsightSection = {
  title: "7.3 Bullpen, Park, Weather (Environment Is Not Optional)",
  pillarTitle: "PILLAR 7 — Deep Dive: How the MLB Simulation Works (Framework Only)",
  body: [
    "A simulation without: bullpen leverage, park factors, wind/temperature …is incomplete.",
    "Your JSON test result proves you're already capturing a ton: batter/pitcher splits, expected stats, park/weather modifiers, availability coverage.",
    "That's a legit foundation.",
  ],
};

export const section4: InsightSection = {
  title: "7.4 From Simulation to Market Outputs (Where Money Is Made)",
  pillarTitle: "PILLAR 7 — Deep Dive: How the MLB Simulation Works (Framework Only)",
  body: [
    "The simulation produces distributions: runs scored, player hits, Ks, HRs, team win probability.",
    "Then we convert those distributions into prices: moneyline, run line, totals, props.",
    "This is why the model is the product. The website is the delivery system.",
  ],
};
