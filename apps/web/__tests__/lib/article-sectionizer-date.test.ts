import { describe, expect, it } from "vitest";
import {
  DEFAULT_ARTICLE_DATE,
  formatArticleAttribution,
  formatArticleDate,
  formatPreviewDate,
} from "@/lib/article-sectionizer";

describe("formatArticleDate", () => {
  it("uses the season-preview default when empty", () => {
    expect(formatArticleDate(null)).toBe(DEFAULT_ARTICLE_DATE);
    expect(formatArticleDate("")).toBe(DEFAULT_ARTICLE_DATE);
  });

  it("normalizes long calendar dates", () => {
    expect(formatArticleDate("July 29, 2026")).toBe("July 29, 2026");
  });

  it("keeps time when requested", () => {
    expect(
      formatArticleDate("July 29, 2026 · 2:15 PM ET", { includeTime: true }),
    ).toBe("July 29, 2026 · 2:15 PM ET");
  });

  it("strips time by default for card consistency", () => {
    expect(formatArticleDate("July 29, 2026 · 2:15 PM ET")).toBe(
      "July 29, 2026",
    );
  });

  it("strips leaked writer bylines from the date field", () => {
    expect(formatArticleDate("By Jordan Vale · July 29, 2026")).toBe(
      "July 29, 2026",
    );
  });
});

describe("formatArticleAttribution", () => {
  it("prefixes KosEdge by default", () => {
    expect(formatArticleAttribution("July 29, 2026")).toBe(
      "KosEdge · July 29, 2026",
    );
  });

  it("can return date only", () => {
    expect(
      formatArticleAttribution("July 29, 2026 · 2:15 PM ET", {
        brand: false,
      }),
    ).toBe("July 29, 2026");
  });
});

describe("formatPreviewDate", () => {
  it("delegates to formatArticleDate", () => {
    expect(formatPreviewDate(null)).toBe(DEFAULT_ARTICLE_DATE);
  });
});
