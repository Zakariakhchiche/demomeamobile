import { describe, it, expect, vi, beforeEach } from "vitest";
import type { CfnewsTarget, CfnewsVeilleResponse, CfnewsMeta } from "@/types";

/**
 * CFNEWS Veille — Frontend Tests
 * Tests for API fetch patterns, type safety, and widget data handling.
 */

// ---------------------------------------------------------------------------
// Simulate the fetch pattern used by useCfnews hook
// ---------------------------------------------------------------------------

async function fetchCfnewsVeille(
  limite: number = 10
): Promise<CfnewsVeilleResponse | null> {
  try {
    const res = await fetch(`/api/cfnews/veille?limite=${limite}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_CFNEWS_META: CfnewsMeta = {
  titre: "Tra-C Industrie soude son capital",
  categorie: "Capital developpement",
  url: "https://www.cfnews.net/L-actualite/Capital-developpement/Operations/Tra-C-645731",
  date: "15 avril 2026",
};

const MOCK_CFNEWS_TARGET: CfnewsTarget = {
  id: "cfnews-645731",
  siren: "999888777",
  name: "TRA-C INDUSTRIE",
  sector: "Industrial Tech / TIC",
  sub_sector: "",
  region: "Pays de la Loire",
  city: "NANTES",
  code_naf: "25.62A",
  creation_date: "2001-01-01",
  structure: "Familiale",
  publication_status: "Publie",
  globalScore: 55,
  priorityLevel: "Qualification",
  dirigeants: [
    { name: "Philippe MARTIN", role: "President", age: 64, since: "2001" },
  ],
  financials: {
    revenue: "56.0M EUR",
    revenue_growth: "+16.7%",
    ebitda: "8.4M EUR",
    ebitda_margin: "15.0%",
    ebitda_range: "3-10M",
    effectif: 200,
    last_published_year: 2024,
  },
  topSignals: [
    {
      id: "founder_60_no_successor",
      label: "Fondateur > 60 ans",
      source: "Pappers",
      source_url: "",
      dimension: "maturite_dirigeant",
      points: 15,
      severity: "high",
      family: "Dirigeant",
    },
  ],
  cfnews: MOCK_CFNEWS_META,
  source: "cfnews+pappers",
};

const MOCK_RESPONSE: CfnewsVeilleResponse = {
  data: [MOCK_CFNEWS_TARGET],
  total: 1,
  source: "cfnews-veille",
};

// =========================================================================
// 1. API Fetch Tests
// =========================================================================

describe("CFNEWS API fetch patterns", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchCfnewsVeille returns data on 200", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(MOCK_RESPONSE), { status: 200 })
    );
    const result = await fetchCfnewsVeille(10);
    expect(result).not.toBeNull();
    expect(result!.data).toHaveLength(1);
    expect(result!.total).toBe(1);
    expect(result!.source).toBe("cfnews-veille");
  });

  it("fetchCfnewsVeille returns null on 502 (cfnews down)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("Bad Gateway", { status: 502 })
    );
    const result = await fetchCfnewsVeille();
    expect(result).toBeNull();
  });

  it("fetchCfnewsVeille returns null on network error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new Error("Network failure")
    );
    const result = await fetchCfnewsVeille();
    expect(result).toBeNull();
  });

  it("fetchCfnewsVeille passes limite parameter", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ data: [], total: 0, source: "cfnews-veille" }), {
        status: 200,
      })
    );
    await fetchCfnewsVeille(5);
    expect(fetchSpy).toHaveBeenCalledWith("/api/cfnews/veille?limite=5");
  });

  it("fetchCfnewsVeille handles empty data array", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ data: [], total: 0, source: "cfnews-veille" }),
        { status: 200 }
      )
    );
    const result = await fetchCfnewsVeille();
    expect(result).not.toBeNull();
    expect(result!.data).toHaveLength(0);
    expect(result!.total).toBe(0);
  });
});

// =========================================================================
// 2. Type Safety Tests
// =========================================================================

describe("CFNEWS type safety", () => {
  it("CfnewsTarget extends Target with cfnews and source", () => {
    const target: CfnewsTarget = MOCK_CFNEWS_TARGET;
    // Standard Target fields
    expect(target.id).toBeDefined();
    expect(target.name).toBeDefined();
    expect(target.globalScore).toBeGreaterThanOrEqual(0);
    expect(target.priorityLevel).toBeDefined();
    expect(target.dirigeants).toBeDefined();
    expect(target.financials).toBeDefined();
    expect(target.topSignals).toBeDefined();

    // CFNEWS-specific fields
    expect(target.cfnews).toBeDefined();
    expect(target.cfnews!.titre).toBe("Tra-C Industrie soude son capital");
    expect(target.cfnews!.url).toContain("cfnews.net");
    expect(target.source).toBe("cfnews+pappers");
  });

  it("CfnewsTarget works with optional cfnews (cfnews-only fallback)", () => {
    const target: CfnewsTarget = {
      ...MOCK_CFNEWS_TARGET,
      siren: "",
      globalScore: 0,
      priorityLevel: "Veille Passive",
      source: "cfnews-only",
    };
    expect(target.cfnews?.titre ?? "—").toBe(
      "Tra-C Industrie soude son capital"
    );
    expect(target.source).toBe("cfnews-only");
  });

  it("CfnewsTarget with missing cfnews uses optional chaining safely", () => {
    const target: CfnewsTarget = {
      ...MOCK_CFNEWS_TARGET,
      cfnews: undefined,
    };
    expect(target.cfnews?.titre ?? "—").toBe("—");
    expect(target.cfnews?.url ?? "#").toBe("#");
    expect(target.cfnews?.categorie ?? "N/A").toBe("N/A");
  });
});

// =========================================================================
// 3. Widget Data Processing Tests
// =========================================================================

describe("CFNEWS widget data processing", () => {
  it("sorts targets by score descending", () => {
    const targets: CfnewsTarget[] = [
      { ...MOCK_CFNEWS_TARGET, id: "1", globalScore: 30 },
      { ...MOCK_CFNEWS_TARGET, id: "2", globalScore: 75 },
      { ...MOCK_CFNEWS_TARGET, id: "3", globalScore: 50 },
    ];
    const sorted = [...targets].sort(
      (a, b) => b.globalScore - a.globalScore
    );
    expect(sorted[0].globalScore).toBe(75);
    expect(sorted[1].globalScore).toBe(50);
    expect(sorted[2].globalScore).toBe(30);
  });

  it("slices to top 5 for widget display", () => {
    const targets: CfnewsTarget[] = Array.from({ length: 10 }, (_, i) => ({
      ...MOCK_CFNEWS_TARGET,
      id: `t-${i}`,
      globalScore: i * 10,
    }));
    const widget = targets.slice(0, 5);
    expect(widget).toHaveLength(5);
  });

  it("handles zero-score targets without crashing", () => {
    const target: CfnewsTarget = {
      ...MOCK_CFNEWS_TARGET,
      globalScore: 0,
      topSignals: [],
      source: "cfnews-only",
    };
    const scorePercent = Math.min(target.globalScore, 100);
    expect(scorePercent).toBe(0);
    expect(target.topSignals).toHaveLength(0);
  });

  it("assigns correct color class based on score", () => {
    function scoreColor(score: number): string {
      if (score >= 65) return "emerald";
      if (score >= 45) return "indigo";
      if (score >= 25) return "amber";
      return "gray";
    }
    expect(scoreColor(80)).toBe("emerald");
    expect(scoreColor(55)).toBe("indigo");
    expect(scoreColor(35)).toBe("amber");
    expect(scoreColor(10)).toBe("gray");
    expect(scoreColor(0)).toBe("gray");
    expect(scoreColor(65)).toBe("emerald");
    expect(scoreColor(45)).toBe("indigo");
    expect(scoreColor(25)).toBe("amber");
  });

  it("extracts cfnews.url for external link", () => {
    const url = MOCK_CFNEWS_TARGET.cfnews?.url ?? "#";
    expect(url).toMatch(/^https:\/\/www\.cfnews\.net\//);
  });
});
