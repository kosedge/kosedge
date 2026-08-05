import type { RiskFlag } from "@/lib/fantasy/types";

export type DepthRow = {
  team: string;
  position: string;
  depthOrder: number;
  playerName: string;
  roleConfidence: number;
};

function normalizeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .replace(/jr$|sr$|ii$|iii$|iv$/, "");
}

function nameMatch(a: string, b: string): boolean {
  const na = normalizeName(a);
  const nb = normalizeName(b);
  if (!na || !nb) return false;
  return na === nb || na.includes(nb) || nb.includes(na);
}

/**
 * Concise risk flags from depth chart + projection shape.
 * Honest when thin — we do not invent injury grades without a feed.
 */
export function buildRiskFlags(input: {
  playerName: string;
  team: string;
  position: string;
  isRookie: boolean;
  gamesProjected: number;
  rushYardsTotal: number;
  depthRows: DepthRow[];
  teammateRushYards: Array<{ playerName: string; rushYards: number }>;
}): RiskFlag[] {
  const flags: RiskFlag[] = [];
  const pos = input.position.toUpperCase();
  const teamDepth = input.depthRows.filter(
    (row) =>
      row.team.toUpperCase() === input.team.toUpperCase() &&
      row.position.toUpperCase() === pos,
  );
  const self = teamDepth.find((row) =>
    nameMatch(row.playerName, input.playerName),
  );

  if (input.isRookie) {
    flags.push({
      kind: "rookie",
      label: "Rookie",
      detail: "No NFL track record — outcome band is wider than a veteran peer.",
    });
  }

  if (input.gamesProjected > 0 && input.gamesProjected < 15) {
    flags.push({
      kind: "availability",
      label: "Availability",
      detail: `Only ${input.gamesProjected} games projected — durability/role path is thinner than a full slate.`,
    });
  }

  if (self && self.depthOrder > 1) {
    flags.push({
      kind: "depth_volatility",
      label: "Depth chart",
      detail: `Listed depth ${self.depthOrder} (confidence ${self.roleConfidence.toFixed(2)}) — role can swing with camp/in-season reshuffles.`,
    });
  } else if (self && self.roleConfidence < 0.7) {
    flags.push({
      kind: "depth_volatility",
      label: "Role volatility",
      detail: `Starter-slot confidence ${self.roleConfidence.toFixed(2)} — murky pecking order.`,
    });
  }

  if (pos === "RB" && input.rushYardsTotal >= 350) {
    const rivals = input.teammateRushYards
      .filter(
        (row) =>
          !nameMatch(row.playerName, input.playerName) && row.rushYards >= 350,
      )
      .sort((a, b) => b.rushYards - a.rushYards);
    if (rivals[0]) {
      const share =
        input.rushYardsTotal /
        (input.rushYardsTotal + rivals[0].rushYards + 1e-6);
      if (share < 0.62) {
        flags.push({
          kind: "committee",
          label: "Committee",
          detail: `Backfield share pressure vs ${rivals[0].playerName} (${rivals[0].rushYards.toFixed(0)} rush yds) — not a clear feature back.`,
        });
      }
    }
  }

  if (pos === "WR") {
    const wrDepth = teamDepth.filter((row) => row.depthOrder <= 3);
    if (wrDepth.length >= 3) {
      const murky = wrDepth.every((row) => row.roleConfidence <= 0.7);
      if (murky || (self && self.depthOrder >= 2)) {
        // only flag if self is not a clear WR1
        if (!self || self.depthOrder >= 2) {
          flags.push({
            kind: "depth_volatility",
            label: "WR room",
            detail: "Crowded target hierarchy — weekly target share can swing.",
          });
        }
      }
    }
  }

  return flags.slice(0, 3);
}
