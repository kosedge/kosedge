export type MarkdownSection = {
  heading: string | null;
  content: string;
};

export type HandicappersNote = {
  fairNumber: string | null;
  marketNumber: string | null;
  lean: string | null;
  confidence: string | null;
  keyRisk: string | null;
  disclaimer: string | null;
  raw: string | null;
};

export type TeamPreviewSlots = {
  bottomLine: string;
  introBody: string;
  theNumber: string;
  quickProjection: string;
  rosterSnapshot: string;
  whatMattersMost: string;
  scheduleNotes: string;
  bettingAngles: string;
  whatWouldChange: string;
  remainingBody: string;
  handicappersNote: HandicappersNote;
};

export type NewsUpdateSlots = {
  bottomLine: string;
  keyPoints: string[];
  bodySections: MarkdownSection[];
  watchNext: string;
  sources: string | null;
  handicappersNote: HandicappersNote;
};

const DISCLAIMER =
  /This analysis is for informational and educational purposes only\.[\s\S]*$/i;

function stripDisclaimer(text: string): { body: string; disclaimer: string | null } {
  const match = text.match(DISCLAIMER);
  if (!match) return { body: text.trim(), disclaimer: null };
  return {
    body: text.slice(0, match.index).trim(),
    disclaimer: match[0].trim(),
  };
}

export function splitMarkdownSections(markdown: string): MarkdownSection[] {
  const lines = markdown.split(/\r?\n/);
  const sections: MarkdownSection[] = [];
  let current: MarkdownSection = { heading: null, content: "" };

  for (const line of lines) {
    const h2 = line.match(/^##\s+(.+)$/);
    if (h2) {
      if (current.content.trim() || current.heading !== null) {
        sections.push({ ...current, content: current.content.trim() });
      }
      current = { heading: h2[1].trim(), content: "" };
      continue;
    }
    current.content += `${line}\n`;
  }

  if (current.content.trim() || current.heading !== null) {
    sections.push({ ...current, content: current.content.trim() });
  }

  return sections;
}

export function extractHandicappersNote(source: string): HandicappersNote {
  const blockMatch = source.match(
    /\*\*Handicapper['\u2019]s Note\*\*\s*([\s\S]*?)(?=\n\nThis analysis is for informational|$)/i,
  );
  const raw = blockMatch?.[0]?.trim() ?? null;
  const inner = blockMatch?.[1]?.trim() ?? "";

  const pick = (label: string): string | null => {
    const re = new RegExp(`${label}:\\s*(.+?)\\s*(?:\\n|$)`, "i");
    return inner.match(re)?.[1]?.trim() ?? null;
  };

  const disclaimerMatch = source.match(DISCLAIMER);

  return {
    fairNumber: pick("Fair number"),
    marketNumber: pick("Market number"),
    lean: pick("Lean"),
    confidence: pick("Confidence"),
    keyRisk: pick("Key risk"),
    disclaimer: disclaimerMatch?.[0]?.trim() ?? null,
    raw,
  };
}

function removeHandicappersBlock(text: string): string {
  return text
    .replace(
      /\*\*Handicapper['\u2019]s Note\*\*[\s\S]*?(?=\n\nThis analysis is for informational|$)/i,
      "",
    )
    .replace(DISCLAIMER, "")
    .trim();
}

function matchTeamPreviewSlot(heading: string): keyof TeamPreviewSlots | null {
  const h = heading.toLowerCase();

  if (/betting guide|betting angles/.test(h)) return "bettingAngles";
  if (
    /division|market vs model|contender roster|profile|one primary number|two fair numbers|two seasons|rebuild timeline|opening frame|lead with the division|defense is the prior|three sustainability|speed that is left|inventory the noise|totals market first|why the qb/.test(
      h,
    )
  ) {
    return "quickProjection";
  }
  if (
    /camp signal|camp:|latrobe|greenbrier|pittsford|participation|starter locked|contract year|availability is|the competition is|defense and the|qb development|camp shock|camp structure|camp:/.test(
      h,
    )
  ) {
    return "whatMattersMost";
  }
  if (/roster|depth chart|bubble|receiver room|offense after|aging pieces/.test(h)) {
    return "rosterSnapshot";
  }
  if (
    /schedule|path|opening frame|steal weeks|hard card|gauntlet|september sides|how .* actually cashes/.test(
      h,
    )
  ) {
    return "scheduleNotes";
  }
  if (
    /what (the )?market|what to watch|camp revisit|before the number|where the public|model conflict|model check|why .* clears/.test(
      h,
    )
  ) {
    return "whatWouldChange";
  }
  if (
    /\d+\.\d+|win total|primary number|market math|the \d|six years|one expensive|present both|direction agrees|fair sits/.test(
      h,
    )
  ) {
    return "theNumber";
  }

  return null;
}

function firstParagraphs(text: string, count = 2): string {
  const paras = text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p && !p.startsWith("#") && !p.startsWith("|"));
  return paras.slice(0, count).join("\n\n");
}

function joinSections(sections: MarkdownSection[]): string {
  return sections
    .map((s) => (s.heading ? `## ${s.heading}\n\n${s.content}` : s.content))
    .filter(Boolean)
    .join("\n\n")
    .trim();
}

export function sectionizeTeamPreview(bodyMarkdown: string): TeamPreviewSlots {
  const handicappersNote = extractHandicappersNote(bodyMarkdown);
  const cleaned = removeHandicappersBlock(bodyMarkdown);
  const sections = splitMarkdownSections(cleaned);

  const intro = sections.find((s) => s.heading === null)?.content ?? "";
  const introParas = intro.split(/\n\s*\n/).filter(Boolean);
  const bottomLine = introParas[0]?.trim() ?? "";
  const introBody = introParas.slice(1).join("\n\n").trim();

  const buckets: Record<string, MarkdownSection[]> = {
    theNumber: [],
    quickProjection: [],
    rosterSnapshot: [],
    whatMattersMost: [],
    scheduleNotes: [],
    bettingAngles: [],
    whatWouldChange: [],
    remainingBody: [],
  };

  for (const section of sections) {
    if (section.heading === null) continue;
    const slot = matchTeamPreviewSlot(section.heading);
    const key = slot ?? "remainingBody";
    buckets[key].push(section);
  }

  return {
    bottomLine,
    introBody,
    theNumber: joinSections(buckets.theNumber),
    quickProjection: joinSections([
      ...buckets.quickProjection,
      ...(introBody ? [{ heading: null, content: introBody }] : []),
    ]),
    rosterSnapshot: joinSections(buckets.rosterSnapshot),
    whatMattersMost: joinSections(buckets.whatMattersMost),
    scheduleNotes: joinSections(buckets.scheduleNotes),
    bettingAngles: joinSections(buckets.bettingAngles),
    whatWouldChange: joinSections(buckets.whatWouldChange),
    remainingBody: joinSections(buckets.remainingBody),
    handicappersNote,
  };
}

function extractBulletKeyPoints(text: string): string[] {
  const lines = text.split(/\r?\n/);
  const points: string[] = [];
  for (const line of lines) {
    const bullet = line.match(/^[-*]\s+\*\*(.+?):\*\*\s*(.+)$/);
    if (bullet) {
      points.push(`${bullet[1]}: ${bullet[2]}`);
      continue;
    }
    const simple = line.match(/^[-*]\s+(.+)$/);
    if (simple && !simple[1].startsWith("**Handicapper")) {
      points.push(simple[1].replace(/\*\*/g, "").trim());
    }
  }
  return points.slice(0, 6);
}

export function sectionizeNewsUpdate(bodyMarkdown: string): NewsUpdateSlots {
  const handicappersNote = extractHandicappersNote(bodyMarkdown);
  const cleaned = removeHandicappersBlock(bodyMarkdown);
  const sections = splitMarkdownSections(cleaned);

  const intro = sections.find((s) => s.heading === null)?.content ?? "";
  const introParas = intro.split(/\n\s*\n/).filter(Boolean);
  const bottomLine = introParas[0]?.trim() ?? "";

  const keyPointSection = sections.find((s) =>
    /key point|facts|at a glance|quick read/i.test(s.heading ?? ""),
  );
  const keyPoints = keyPointSection
    ? extractBulletKeyPoints(keyPointSection.content)
    : extractBulletKeyPoints(intro);

  const watchSection = sections.find((s) =>
    /what to watch|watch next|next check|implication/i.test(s.heading ?? ""),
  );

  const bodySections = sections.filter(
    (s) =>
      s.heading !== null &&
      s !== keyPointSection &&
      s !== watchSection &&
      !/sources/i.test(s.heading ?? ""),
  );

  const sourcesSection = sections.find((s) => /sources/i.test(s.heading ?? ""));

  return {
    bottomLine,
    keyPoints,
    bodySections,
    watchNext: watchSection?.content ?? "",
    sources: sourcesSection?.content ?? null,
    handicappersNote,
  };
}

export function extractInlineSources(markdown: string): string | null {
  const match = markdown.match(/\*\*Sources(?: \(beat desk\))?:\*\*\s*(.+?)\s*$/im);
  return match?.[1]?.trim() ?? null;
}

export function formatPreviewDate(value: string | null | undefined): string {
  if (value) return value;
  return "July 29, 2026";
}
