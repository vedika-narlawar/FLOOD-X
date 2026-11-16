import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Overview from "./pages/Overview";
import Explorer from "./pages/Explorer";
import Scenario from "./pages/Scenario";
import Rainfall from "./pages/Rainfall";
import { Unavailable } from "./components/ui";
import { ApiError } from "./api";

vi.mock("./components/MapView", () => ({
  default: (p: any) => <div data-testid="map" data-grid={p.grid ? "yes" : "no"} data-wards={p.wards ? "yes" : "no"} />,
  CAT_COLORS: {}, rampColor: () => "#000",
}));

type Routes = Record<string, { status?: number; body: any }>;
function mockFetch(routes: Routes) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    calls.push(url);
    const key = Object.keys(routes).find((k) => url.startsWith(k));
    const r = key ? routes[key] : { status: 503, body: { detail: { status: "unavailable", module: "x", reason: `no route ${url}`, upstream_stages: {} } } };
    return { ok: (r.status ?? 200) < 400, status: r.status ?? 200, json: async () => r.body } as Response;
  }));
  return calls;
}
const wrap = (ui: JSX.Element) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>);
const unavail = (reason: string, upstream: any = {}) => ({ status: 503, body: { detail: { status: "unavailable", module: "m", reason, upstream_stages: upstream } } });

beforeEach(() => { vi.unstubAllGlobals(); });
afterEach(() => { vi.unstubAllGlobals(); });

describe("Unavailable", () => {
  it("shows reason and upstream stage evidence", () => {
    render(<Unavailable error={new ApiError(503, { status: "unavailable", reason: "DEM missing", upstream_stages: { download_dem: { status: "blocked", message: "DNS failed" } } })} />);
    expect(screen.getByRole("alert")).toHaveTextContent("DEM missing");
    expect(screen.getByText("download_dem")).toBeInTheDocument();
    expect(screen.getByText(/DNS failed/)).toBeInTheDocument();
  });
  it("distinguishes an unreachable backend", () => {
    render(<Unavailable error={new ApiError(0, { status: "backend_unreachable", reason: "Cannot reach the FLOOD-X backend" })} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/Backend unreachable/i);
  });
});

describe("Overview shows only backend data", () => {
  it("renders KPI values from the API response (no hardcoded numbers)", async () => {
    mockFetch({
      "/api/metadata": { body: { study_area: { area_km2: 123.4, n_wards: 7, analysis_crs: "EPSG:32643" } } },
      "/api/status": { body: { datasets_by_status: { ready_for_analysis: 2, blocked_in_environment: 3 }, stages_by_status: { success: 4, blocked: 1 }, susceptibility_available: false } },
      "/api/boundaries/wards": { body: { type: "FeatureCollection", features: [] } },
      "/api/pipeline/status": { body: { stages: { download_dem: { status: "blocked", message: "DNS fail" } } } },
    });
    wrap(<Overview />);
    expect(await screen.findByText("123.4")).toBeInTheDocument();
    expect(screen.getByText("not generated")).toBeInTheDocument();
    expect(await screen.findByText(/DNS fail/)).toBeInTheDocument();
  });
  it("shows error states and no KPI tiles when every endpoint fails", async () => {
    mockFetch({});
    wrap(<Overview />);
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(2));
    expect(screen.queryByText("km²")).not.toBeInTheDocument();
    expect(screen.queryByText("Wards (PMC + PCMC)")).not.toBeInTheDocument();
  });
});

describe("Explorer", () => {
  const base = {
    "/api/boundaries/wards": { body: { type: "FeatureCollection", features: [{ type: "Feature", properties: { ward_id: 1, ward_name: "Aundh" }, geometry: null }, { type: "Feature", properties: { ward_id: 2, ward_name: "Kothrud" }, geometry: null }] } },
    "/api/datasets": { body: [{ id: "dem_cop_glo30", status: "blocked_in_environment", blocker: "DNS" }] },
  };
  it("disables unavailable analytical layers and explains why", async () => {
    mockFetch({ ...base, "/api/susceptibility/grid": unavail("no grid"), "/api/exposure/facilities": unavail("no osm") });
    wrap(<Explorer />);
    const cb = await screen.findByLabelText(/Susceptibility grid/);
    await waitFor(() => expect(cb).toBeDisabled());
    expect(screen.getAllByText("unavailable").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/No susceptibility layer yet/)).toBeInTheDocument();
  });
  it("ward search filters, and category filter changes the API request", async () => {
    const feat = { type: "Feature", properties: { score: 50, category: "High", elev_mean_m: 600 }, geometry: null };
    const calls = mockFetch({ ...base, "/api/susceptibility/grid": { body: { type: "FeatureCollection", features: [feat], metadata: {} } }, "/api/exposure/facilities": unavail("no osm") });
    wrap(<Explorer />);
    fireEvent.change(screen.getByLabelText("Search ward"), { target: { value: "koth" } });
    expect(await screen.findByText("Kothrud")).toBeInTheDocument();
    expect(screen.queryByText("Aundh")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText(/Susceptibility grid/)).not.toBeDisabled());
    const catSelect = screen.getAllByRole("combobox").find((el) => (el as HTMLSelectElement).value === "" && el.textContent?.includes("Very high"))!;
    fireEvent.change(catSelect, { target: { value: "High" } });
    await waitFor(() => expect(calls.some((c) => c.includes("category=High"))).toBe(true));
  });
});

describe("Scenario Studio", () => {
  const cfg = { body: { variables: [{ name: "builtup_share", weight: 0.2, direction: "increase" }] } };
  it("disables evaluation with the backend's reason when the index is unavailable", async () => {
    mockFetch({ "/api/susceptibility/config": cfg, "/api/susceptibility/metadata": unavail("Screening index has not been computed") });
    wrap(<Scenario />);
    const btn = await screen.findByRole("button", { name: /Evaluate scenario/i });
    await waitFor(() => expect(btn).toBeDisabled());
    expect(screen.getByText(/Screening index has not been computed/)).toBeInTheDocument();
  });
  it("posts the configured weights and renders returned comparison, including not-applied rainfall", async () => {
    const calls: any[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: any) => {
      calls.push([url, init?.body]);
      const body = url.includes("config") ? cfg.body : url.includes("metadata") ? { ok: 1 } : {
        scenario_id: "abc123", assumptions: ["Only weights differ"], not_applied: [{ parameter: "rainfall_multiplier / window_hours", reason: "no runoff model" }],
        comparison: { spearman_rank_correlation: 0.91, cells_changing_category: 17, n_cells_compared: 100, mean_score: { baseline: 50, scenario: 52 },
          score_histogram_bins_0_100: { baseline: Array(10).fill(1), scenario: Array(10).fill(1) }, zone_ranking: [{ zone: "Aundh", baseline_rank: 2, scenario_rank: 1, rank_change: 1 }] } };
      return { ok: true, status: 200, json: async () => body } as Response;
    }));
    wrap(<Scenario />);
    const btn = await screen.findByRole("button", { name: /Evaluate scenario/i });
    await waitFor(() => expect(btn).not.toBeDisabled());
    fireEvent.change(screen.getByLabelText("Weight builtup_share"), { target: { value: "0.8" } });
    fireEvent.click(btn);
    expect(await screen.findByText("0.91")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.getByText(/no runoff model/)).toBeInTheDocument();
    const posted = JSON.parse(calls.find((c) => c[0] === "/api/scenarios/evaluate")![1]);
    expect(posted.weights.builtup_share).toBe(0.8);
  });
});

describe("Rainfall", () => {
  it("shows the unavailable reason, never an empty success", async () => {
    mockFetch({ "/api/rainfall": unavail("Open-Meteo unreachable", { download_rainfall: { status: "blocked", message: "DNS" } }) });
    wrap(<Rainfall />);
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(0));
    expect(screen.getAllByText(/Open-Meteo unreachable/).length).toBeGreaterThan(0);
  });
});
