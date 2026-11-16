"""Fix: grid-cell clicks showed ward info because the filled ward layer sat on top of the grid.
Safe & idempotent: checks anchors, backs up every file it changes, writes a new test file."""
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "frontend" / "src" / "components" / "MapView.tsx"
EXP = ROOT / "frontend" / "src" / "pages" / "Explorer.tsx"
TEST = ROOT / "frontend" / "src" / "gridclick.test.tsx"


def read(p):
    raw = p.read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write(p, text, crlf):
    p.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit(f"STOP: anchor for '{label}' found {n} times (expected 1). Nothing was changed for this file. Send me this message.")
    return text.replace(old, new)


for p in (MAP, EXP):
    if not p.exists():
        sys.exit(f"STOP: {p} not found. Run this from your flood-x folder.")

map_t, map_crlf = read(MAP)
exp_t, exp_crlf = read(EXP)
need_map = "wardsInteractive" not in map_t
need_exp = "function CellDetails" not in exp_t

if need_map:
    map_t = once(map_t, "export default function MapView({",
                 "// Ward polygons are filled; if they stay interactive on top of the grid they swallow every click.\n"
                 "export const wardsInteractive = (gridVisible: boolean) => !gridVisible;\n\nexport default function MapView({", "helper")
    map_t = once(map_t, "}: MapProps) {\n", "}: MapProps) {\n  const gridActive = !!grid?.features?.length;\n", "gridActive")
    map_t = once(map_t, "layers.current.wards = L.geoJSON(wards, {",
                 "layers.current.wards = L.geoJSON(wards, {\n        interactive: wardsInteractive(gridActive),", "wards layer")
    map_t = once(map_t, "}, [wards, showWards, selectedWard, dim, onSelect]);",
                 "}, [wards, showWards, selectedWard, dim, onSelect, gridActive]);", "wards deps")

if need_exp:
    comp = '''function CellDetails({ p }: { p: Record<string, any> }) {
  const num = (k: string, d: number, unit = "") => (typeof p[k] === "number" && Number.isFinite(p[k]) ? `${fmt(p[k], d)}${unit}` : "not available");
  const rows: [string, string][] = [
    ["Cell ID", p.cell_id ?? "not available"],
    ["Susceptibility score", num("score", 1, " / 100")],
    ["Category", p.category ?? "not available"],
    ["Inputs used", typeof p.n_inputs_used === "number" ? String(p.n_inputs_used) : "not available"],
    ["Elevation (mean)", num("elev_mean_m", 1, " m")],
    ["Slope (mean)", num("slope_mean_deg", 2, " deg")],
    ["Relative elevation", num("rel_elev_mean_m", 2, " m")],
    ["Distance to waterway", num("dist_waterway_m", 0, " m")],
    ["Ward", p.ward_name ?? "-"],
  ];
  return (
    <table className="w-full" data-testid="cell-details"><tbody>
      {rows.map(([k, v]) => <tr key={k}><Td>{k}</Td><Td right mono>{v}</Td></tr>)}
    </tbody></table>
  );
}

'''
    exp_t = once(exp_t, "export default function Explorer() {", comp + "export default function Explorer() {", "component")
    start_tok = '<table className="w-full"><tbody>{Object.entries(sel.props)'
    exp_t = once(exp_t, start_tok, start_tok, "table start")
    s = exp_t.index(start_tok)
    e = exp_t.index("</tbody></table>", s) + len("</tbody></table>")
    orig = exp_t[s:e]
    exp_t = exp_t[:s] + '{sel.kind === "cell" ? <CellDetails p={sel.props} /> : (' + orig + ")}" + exp_t[e:]

TEST_SRC = '''import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import Explorer from "./pages/Explorer";

vi.mock("./components/MapView", () => ({
  default: (p: any) => (
    <div>
      <button onClick={() => p.onSelect("cell", { cell_id: "c500_00042", score: 81.34, category: "Very high", n_inputs_used: 4, elev_mean_m: 551.2, slope_mean_deg: 1.234, rel_elev_mean_m: -3.5, dist_waterway_m: 120.4, ward_id: 7, ward_name: "Test Ward", municipality: "PMC" })}>pick-cell</button>
      <button onClick={() => p.onSelect("cell", { cell_id: "c500_00043", score: 40, category: "Low", n_inputs_used: 3, elev_mean_m: null })}>pick-sparse-cell</button>
      <button onClick={() => p.onSelect("ward", { ward_id: 7, ward_name: "Test Ward", municipality: "PMC" })}>pick-ward</button>
    </div>
  ),
  CAT_COLORS: {}, rampColor: () => "#000",
}));

function setup() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const ok = (body: any) => ({ ok: true, status: 200, json: async () => body }) as Response;
    if (url.startsWith("/api/boundaries/wards")) return ok({ type: "FeatureCollection", features: [] });
    if (url.startsWith("/api/datasets")) return ok([]);
    return { ok: false, status: 503, json: async () => ({ detail: { status: "unavailable", reason: "n/a", upstream_stages: {} } }) } as Response;
  }));
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><Explorer /></QueryClientProvider>);
}

describe("Inspector shows the selected object", () => {
  it("shows cell details (not ward fields) for a grid cell", async () => {
    setup();
    fireEvent.click(await screen.findByText("pick-cell"));
    const t = await screen.findByTestId("cell-details");
    expect(t).toHaveTextContent("c500_00042");
    expect(t).toHaveTextContent("81.3 / 100");
    expect(t).toHaveTextContent("Very high");
    expect(t).toHaveTextContent("Inputs used4");
    expect(t).toHaveTextContent("551.2 m");
    expect(t).toHaveTextContent("1.23 deg");
    expect(t).toHaveTextContent("-3.5 m");
    expect(t).toHaveTextContent("120 m");
    expect(screen.queryByText("municipality")).not.toBeInTheDocument();
  });
  it("marks missing cell values as not available instead of inventing them", async () => {
    setup();
    fireEvent.click(await screen.findByText("pick-sparse-cell"));
    const t = await screen.findByTestId("cell-details");
    expect(t).toHaveTextContent("c500_00043");
    expect(t).toHaveTextContent("Elevation (mean)not available");
    expect(t).toHaveTextContent("Slope (mean)not available");
  });
  it("still shows ward fields for a ward selection", async () => {
    setup();
    fireEvent.click(await screen.findByText("pick-ward"));
    await waitFor(() => expect(screen.getByText("municipality")).toBeInTheDocument());
    expect(screen.queryByTestId("cell-details")).not.toBeInTheDocument();
  });
});

describe("ward layer must not cover grid cells", () => {
  it("is non-interactive while the grid is visible and interactive otherwise", async () => {
    const actual = await vi.importActual<any>("./components/MapView");
    expect(actual.wardsInteractive(true)).toBe(false);
    expect(actual.wardsInteractive(false)).toBe(true);
  });
});
'''

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
bdir = ROOT / "backups" / f"grid-click-{stamp}"
changed = []
for p, text, crlf, need in ((MAP, map_t, map_crlf, need_map), (EXP, exp_t, exp_crlf, need_exp)):
    if need:
        dest = bdir / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        write(p, text, crlf)
        changed.append(p.relative_to(ROOT))
if TEST.exists():
    dest = bdir / TEST.relative_to(ROOT); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(TEST, dest)
TEST.write_text(TEST_SRC, encoding="utf-8")
print("Patched:", [str(c) for c in changed] or "nothing (already patched)")
print("Test file written:", TEST.relative_to(ROOT))
print("Backups in:", bdir if changed else "(none needed)")