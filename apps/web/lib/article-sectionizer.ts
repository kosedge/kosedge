export type MarkdownSection = {
  heading: string | null;
  content: string;
};

export type HandicappersNote = {
  /** Optional label when the note is titled e.g. "Handicapper's Note — Spread". */
  label: string | null;
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

export type DeskHandicapSlots = {
  bottomLine: string;
  bodyMarkdown: string;
  sources: string | null;
  handicappersNotes: HandicappersNote[];
};

const DISCLAIMER =
  /This analysis is for informational and educational purposes only\.[\s\S]*$/i;

function stripDisclaimer(text: string): {
  body: string;
  disclaimer: string | null;
} {
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

function handicappersNoteBlockRegex(): RegExp {
  return /\*\*Handicapper['\u2019]s Note(?:\s*[—\-–]\s*([^*]+))?\*\*\s*([\s\S]*?)(?=\n\*\*Handicapper['\u2019]s Note|\n\nThis analysis is for informational|$)/gi;
}

function parseHandicappersNoteInner(
  inner: string,
  opts: {
    label: string | null;
    raw: string | null;
    disclaimer: string | null;
  },
): HandicappersNote {
  const pick = (field: string): string | null => {
    const re = new RegExp(`${field}:\\s*(.+?)\\s*(?:\\n|$)`, "i");
    return inner.match(re)?.[1]?.trim() ?? null;
  };

  return {
    label: opts.label,
    fairNumber: pick("Fair number"),
    marketNumber: pick("Market number"),
    lean: pick("Lean"),
    confidence: pick("Confidence"),
    keyRisk: pick("Key risk"),
    disclaimer: opts.disclaimer,
    raw: opts.raw,
  };
}

/** Extract every Handicapper's Note block (spread/side/total variants included). */
export function extractHandicappersNotes(source: string): HandicappersNote[] {
  const disclaimerMatch = source.match(DISCLAIMER);
  const disclaimer = disclaimerMatch?.[0]?.trim() ?? null;
  const notes: HandicappersNote[] = [];

  for (const match of source.matchAll(handicappersNoteBlockRegex())) {
    const label = match[1]?.trim() || null;
    const inner = match[2]?.trim() ?? "";
    notes.push(
      parseHandicappersNoteInner(inner, {
        label,
        raw: match[0]?.trim() ?? null,
        disclaimer: null,
      }),
    );
  }

  if (notes.length === 0) {
    return [
      {
        label: null,
        fairNumber: null,
        marketNumber: null,
        lean: null,
        confidence: null,
        keyRisk: null,
        disclaimer,
        raw: null,
      },
    ];
  }

  // Shared footer disclaimer rides on the last note so multi-note UIs show it once.
  notes[notes.length - 1] = {
    ...notes[notes.length - 1],
    disclaimer,
  };

  return notes;
}

/** First Handicapper's Note only — kept for news/preview callers. */
export function extractHandicappersNote(source: string): HandicappersNote {
  return extractHandicappersNotes(source)[0]!;
}

function removeHandicappersBlock(text: string): string {
  return text
    .replace(handicappersNoteBlockRegex(), "")
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
  if (
    /roster|depth chart|bubble|receiver room|offense after|aging pieces/.test(h)
  ) {
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

/**
 * Desk handicaps are continuous prose (rarely H2s) with one or more
 * Handicapper's Notes. Keep the full body — do not drop paragraphs after the dek.
 */
export function sectionizeDeskHandicap(
  bodyMarkdown: string,
  opts?: { angle?: string | null; sources?: string | null },
): DeskHandicapSlots {
  const handicappersNotes = extractHandicappersNotes(bodyMarkdown);
  const cleaned = removeHandicappersBlock(bodyMarkdown);
  const introParas = cleaned
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p && !p.startsWith("#"));

  const angle = opts?.angle?.trim() || null;
  const bottomLine = angle || introParas[0]?.replace(/\*\*/g, "") || "";
  const body =
    angle || !introParas.length
      ? cleaned.trim()
      : introParas.slice(1).join("\n\n").trim() || cleaned.trim();

  return {
    bottomLine,
    bodyMarkdown: body,
    sources: opts?.sources ?? null,
    handicappersNotes,
  };
}

export function extractInlineSources(markdown: string): string | null {
  const match = markdown.match(
    /\*\*Sources(?: \(beat desk\))?:\*\*\s*(.+?)\s*$/im,
  );
  return match?.[1]?.trim() ?? null;
}

/** Default publish date for 2026 season-preview pack when markdown omits Date/Published. */
export const DEFAULT_ARTICLE_DATE = "August 17, 2026";

const LONG_DATE: Intl.DateTimeFormatOptions = {
  month: "long",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
};

/**
 * Normalize article timestamps for display.
 * Accepts "July 29, 2026", "July 29, 2026 · 2:15 PM ET", ISO-ish strings.
 * Strips accidental writer bylines if they leak into the date field.
 */
export function formatArticleDate(
  value: string | null | undefined,
  opts?: { fallback?: string; includeTime?: boolean },
): string {
  const fallback = opts?.fallback ?? DEFAULT_ARTICLE_DATE;
  if (!value?.trim()) return fallback;

  let raw = value.trim();
  // Never surface "By Name · …" as a date/attribution line.
  raw = raw.replace(/^By\s+[^*·|]+?\s*[·|]\s*/i, "").trim();
  if (!raw) return fallback;

  const parts = raw.split(/\s*[·|]\s*/);
  const datePart = parts[0]?.trim() || raw;
  const timePart = parts.slice(1).join(" · ").trim();

  const parsed = Date.parse(datePart);
  if (!Number.isFinite(parsed)) {
    // Unparsed but clean — return date segment only unless time requested.
    if (opts?.includeTime && timePart) return `${datePart} · ${timePart}`;
    return datePart || fallback;
  }

  // Format from UTC noon to avoid off-by-one near timezone edges.
  const safe = new Date(parsed);
  const utcNoon = new Date(
    Date.UTC(safe.getFullYear(), safe.getMonth(), safe.getDate(), 12),
  );
  const formatted = utcNoon.toLocaleDateString("en-US", LONG_DATE);
  if (opts?.includeTime && timePart) {
    return `${formatted} · ${timePart}`;
  }
  return formatted;
}

/** Card/meta line: "KosEdge · July 29, 2026" (or date-only when brand=false). */
export function formatArticleAttribution(
  value: string | null | undefined,
  opts?: { brand?: boolean; includeTime?: boolean; fallback?: string },
): string {
  const date = formatArticleDate(value, {
    fallback: opts?.fallback,
    includeTime: opts?.includeTime,
  });
  if (opts?.brand === false) return date;
  return `KosEdge · ${date}`;
}

/** @deprecated Prefer formatArticleDate — kept for existing callers. */
export function formatPreviewDate(value: string | null | undefined): string {
  return formatArticleDate(value);
}
