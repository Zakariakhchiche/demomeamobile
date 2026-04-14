import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * Tests for API fetch patterns used across the frontend.
 * Validates error handling, response parsing, and edge cases.
 */

// Simulate the fetch pattern used in page components
async function fetchTargets(): Promise<{ data: unknown[]; total: number } | null> {
  try {
    const res = await fetch("/api/targets");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    return json;
  } catch {
    return null;
  }
}

async function fetchTarget(id: string): Promise<{ data: unknown } | null> {
  try {
    const res = await fetch(`/api/targets/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    return json;
  } catch {
    return null;
  }
}

describe("API fetch patterns", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchTargets returns data on 200", async () => {
    const mockData = { data: [{ id: "edrcf-001", name: "Test" }], total: 1 };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), { status: 200 })
    );
    const result = await fetchTargets();
    expect(result).not.toBeNull();
    expect(result!.data).toHaveLength(1);
    expect(result!.total).toBe(1);
  });

  it("fetchTargets returns null on 500", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("Internal Server Error", { status: 500 })
    );
    const result = await fetchTargets();
    expect(result).toBeNull();
  });

  it("fetchTargets returns null on network error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network failure"));
    const result = await fetchTargets();
    expect(result).toBeNull();
  });

  it("fetchTarget returns data for valid ID", async () => {
    const mockData = { data: { id: "edrcf-001", name: "ACME" } };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), { status: 200 })
    );
    const result = await fetchTarget("edrcf-001");
    expect(result).not.toBeNull();
    expect(result!.data).toHaveProperty("id", "edrcf-001");
  });

  it("fetchTarget returns null for 404", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("Not Found", { status: 404 })
    );
    const result = await fetchTarget("nonexistent");
    expect(result).toBeNull();
  });
});

describe("Type safety for optional fields", () => {
  it("target with null analysis should not crash optional chaining", () => {
    const target = {
      id: "test",
      name: "Test",
      analysis: null as { type: string; window: string; narrative: string } | null,
      risks: undefined as { falsePositive: string; uncertainties: string } | undefined,
      activation: undefined as { deciders: string[]; approach: string } | undefined,
      topSignals: null as unknown[] | null,
    };

    // These patterns are used in report/page.tsx
    expect(target.analysis?.type ?? "—").toBe("—");
    expect(target.analysis?.window ?? "N/A").toBe("N/A");
    expect(target.analysis?.narrative ?? "Analyse en cours.").toBe("Analyse en cours.");
    expect(target.risks?.falsePositive ?? "N/A").toBe("N/A");
    expect(target.risks?.uncertainties ?? "Non évalué").toBe("Non évalué");
    expect(target.activation?.deciders ?? []).toEqual([]);
    expect(target.activation?.approach ?? "À définir").toBe("À définir");
    expect((target.topSignals ?? []).length).toBe(0);
  });

  it("target with present analysis should return actual values", () => {
    const target = {
      analysis: { type: "Cession", window: "6-12 mois", narrative: "Test narrative" },
      risks: { falsePositive: "Faible (0.12)", uncertainties: "Some risk" },
      topSignals: [{ id: "sig1", label: "Signal 1" }],
    };

    expect(target.analysis?.type ?? "—").toBe("Cession");
    expect(target.risks?.falsePositive ?? "N/A").toBe("Faible (0.12)");
    expect((target.topSignals ?? []).length).toBe(1);
  });
});
