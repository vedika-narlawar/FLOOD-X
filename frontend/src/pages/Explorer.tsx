import { useCallback, useMemo, useState } from "react";
import { Badge, Panel, Td, Unavailable, fmt } from "../components/ui";
import MapView, { CAT_COLORS, rampColor } from "../components/MapView";
import { useApi } from "../api";

const CATS = ["Very low", "Low", "Moderate", "High", "Very high"];

export default function Explorer() {
  const [cat, setCat] = useState("");
  const [colorBy, setColorBy] = useState("score");
  const [opacity, setOpacity] = useState(0.7);
  const [showWards, setShowWards] = useState(true);
  const [showGrid, setShowGrid] = useState(false);
  const [showZones, setShowZones] = useState(true);
  const [highlight, setHighlight] = useState(true);
  const [resetKey, setResetKey] = useState(0);
  const [showFac, setShowFac] = useState(true);
  const [showWaterways, setShowWaterways] = useState(false);
  const [showRoads, setShowRoads] = useState(false);
  const [showOsmFacilities, setShowOsmFacilities] = useState(false);
  const [showElevation, setShowElevation] = useState(false);
  const [showSlope, setShowSlope] = useState(false);
  const [showLandcover, setShowLandcover] = useState(false);
  const [showPopulation, setShowPopulation] = useState(false);
  const [facType, setFacType] = useState("");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<{ kind: string; props: any } | null>(null);
  const [wardSel, setWardSel] = useState<number | null>(null);
  const wards = useApi<any>("/api/boundaries/wards");
  const grid = useApi<any>(`/api/susceptibility/grid?limit=5000${cat ? `&category=${encodeURIComponent(cat)}` : ""}`);
  const fac = useApi<any>(`/api/exposure/facilities?limit=2000${facType ? `&type=${facType}` : ""}`);
  const ds = useApi<any[]>("/api/datasets");
  const waterways = useApi<any>("/api/map/osm/waterways");
  const roads = useApi<any>("/api/map/osm/roads");
  const osmFacilities = useApi<any>("/api/map/osm/facilities");
  const elevationRaster = useApi<any>("/api/map/raster/elevation");
  const slopeRaster = useApi<any>("/api/map/raster/slope");
  const landcoverRaster = useApi<any>("/api/map/raster/landcover");
  const populationRaster = useApi<any>("/api/map/raster/population");
  const zones = useApi<any>("/api/susceptibility/zones");
  const zonesOk = !zones.isError && !zones.isLoading;
  const onSelect = useCallback((kind: string, props: any) => { setSel({ kind, props }); if (kind === "ward") setWardSel(props.ward_id); }, []);
  const vars = useMemo(() => {
    const f = grid.data?.features?.[0]?.properties ?? {};
    return ["score", "category", ...Object.keys(f).filter((k) => typeof f[k] === "number" && !["score", "n_inputs_used", "clipped_area_m2", "ward_id"].includes(k) && !k.startsWith("contrib_"))];
  }, [grid.data]);
  const range = useMemo<[number, number]>(() => {
    if (colorBy === "score") return [0, 100];
    const v = (grid.data?.features ?? []).map((f: any) => f.properties[colorBy]).filter((x: any) => typeof x === "number");
    return v.length ? [Math.min(...v), Math.max(...v)] : [0, 1];
  }, [grid.data, colorBy]);
  const matches = (wards.data?.features ?? []).filter((f: any) => f.properties.ward_name.toLowerCase().includes(q.toLowerCase())).slice(0, 8);
  const gridOk = !grid.isError && !grid.isLoading, facOk = !fac.isError && !fac.isLoading;

  return (
    <div className="grid grid-cols-12 gap-4" style={{ height: "calc(100vh - 110px)" }}>
      <aside className="col-span-3 space-y-3 overflow-y-auto">
        <Panel title="Layers">
          <label className="flex items-center gap-2 py-1 text-xs"><input type="checkbox" checked={showWards} onChange={(e) => setShowWards(e.target.checked)} /> PMC wards 2022 <Badge s="available" /></label>
          <label className={`flex items-center gap-2 py-1 text-xs ${zonesOk ? "" : "opacity-50"}`} title={zonesOk ? "" : zones.error?.message}>
            <input type="checkbox" disabled={!zonesOk} checked={zonesOk && showZones} onChange={(e) => setShowZones(e.target.checked)} /> Ward susceptibility ranking {!zonesOk && <Badge s="unavailable" />}
          </label>
          <label className={`flex items-center gap-2 py-1 text-xs ${zonesOk || gridOk ? "" : "opacity-50"}`} title={zonesOk || gridOk ? "" : "Needs the susceptibility layer"}>
            <input type="checkbox" disabled={!(zonesOk || gridOk)} checked={(zonesOk || gridOk) && highlight} onChange={(e) => setHighlight(e.target.checked)} /> Highlight higher-susceptibility areas {!(zonesOk || gridOk) && <Badge s="unavailable" />}
          </label>
          <label className={`flex items-center gap-2 py-1 text-xs ${gridOk ? "" : "opacity-50"}`} title={gridOk ? "" : grid.error?.message}>
            <input type="checkbox" disabled={!gridOk} checked={gridOk && showGrid} onChange={(e) => setShowGrid(e.target.checked)} /> Susceptibility grid {!gridOk && <Badge s="unavailable" />}
          </label>
          <label className={`flex items-center gap-2 py-1 text-xs ${facOk ? "" : "opacity-50"}`} title={facOk ? "" : fac.error?.message}>
            <input type="checkbox" disabled={!facOk} checked={facOk && showFac} onChange={(e) => setShowFac(e.target.checked)} /> Facilities (OSM) {!facOk && <Badge s="unavailable" />}
          </label>
<label className="flex items-center gap-2 py-1 text-xs">
  <input
    type="checkbox"
    checked={showWaterways}
    onChange={(e) => setShowWaterways(e.target.checked)}
  />
  Waterways (OSM)
</label>

<label className="flex items-center gap-2 py-1 text-xs">
  <input
    type="checkbox"
    checked={showRoads}
    onChange={(e) => setShowRoads(e.target.checked)}
  />
  Roads (OSM)
</label>

<label className="flex items-center gap-2 py-1 text-xs">
  <input
    type="checkbox"
    checked={showOsmFacilities}
    onChange={(e) => setShowOsmFacilities(e.target.checked)}
  />
  Facilities — raw OSM
</label>
          

              <div className="mt-3 border-t border-line pt-3">
            <p className="mb-2 text-[10px] uppercase tracking-widest text-mute">
              Terrain & raster layers
            </p>

            {([
              ["Elevation", showElevation, setShowElevation, elevationRaster],
              ["Slope", showSlope, setShowSlope, slopeRaster],
              ["Land cover", showLandcover, setShowLandcover, landcoverRaster],
              ["Population", showPopulation, setShowPopulation, populationRaster],
            ] as const).map(([label, checked, setChecked, query]) => (
              <label
                key={label}
                className={`flex items-center gap-2 py-1 text-xs ${query.isError ? "opacity-70" : ""}`}
                title={query.isError ? query.error?.message : ""}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => setChecked(e.target.checked)}
                />
                <span>{label}</span>
                {query.isLoading && (
                  <span className="ml-auto text-[10px] text-mute">Loading…</span>
                )}
                {query.isError && (
                  <Badge s="unavailable" />
                )}
              </label>
            ))}
            <p className="mt-2 text-[10px] text-mute">
              Raster overlays are contextual data layers, not flood predictions.
            </p>
          </div>


        </Panel>
        <Panel title="Filters & style">
          <label className="block text-[10px] uppercase text-mute">Colour by</label>
          <select className="mb-2 w-full border border-line bg-ink px-2 py-1 text-xs" value={colorBy} onChange={(e) => setColorBy(e.target.value)} disabled={!gridOk}>
            {(gridOk ? vars : ["score"]).map((v) => <option key={v}>{v}</option>)}
          </select>
          <label className="block text-[10px] uppercase text-mute">Susceptibility category</label>
          <select className="mb-2 w-full border border-line bg-ink px-2 py-1 text-xs" value={cat} onChange={(e) => setCat(e.target.value)} disabled={!gridOk && !cat}>
            <option value="">All</option>{CATS.map((c) => <option key={c}>{c}</option>)}
          </select>
          <label className="block text-[10px] uppercase text-mute">Facility type</label>
          <select className="mb-2 w-full border border-line bg-ink px-2 py-1 text-xs" value={facType} onChange={(e) => setFacType(e.target.value)} disabled={!facOk && !facType}>
            <option value="">All</option>{["hospital", "clinic", "school", "fire_station", "police"].map((c) => <option key={c}>{c}</option>)}
          </select>
          <label className="block text-[10px] uppercase text-mute">Layer opacity {Math.round(opacity * 100)}%</label>
          <input type="range" min={0.1} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(+e.target.value)} className="w-full" aria-label="Layer opacity" />
        </Panel>
        <button className="w-full border border-line bg-panel px-3 py-1.5 text-xs text-sub hover:bg-raise" onClick={() => { setResetKey((k) => k + 1); setWardSel(null); }}>Reset view to all of Pune (PMC)</button>
        <Panel title="Find ward">
          <input className="w-full border border-line bg-ink px-2 py-1 text-xs" placeholder="Search ward name…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search ward" />
          <ul className="mt-2 max-h-40 overflow-y-auto text-xs">{matches.map((f: any) => (
            <li key={f.properties.ward_id}><button className="w-full px-1 py-1 text-left hover:bg-raise" onClick={() => { setWardSel(f.properties.ward_id); setSel({ kind: "ward", props: f.properties }); }}>{f.properties.ward_name}</button></li>))}</ul>
        </Panel>
      </aside>
      <div className="col-span-6 flex min-h-0 flex-col border border-line">
        <div className="min-h-0 flex-1">
          {wards.isError ? <Unavailable error={wards.error} /> :
            <MapView
  wards={wards.data}
  waterways={waterways.data}
  roads={roads.data}
  osmFacilities={osmFacilities.data}
  showWaterways={showWaterways}
  showRoads={showRoads}
  showOsmFacilities={showOsmFacilities}
  elevationRaster={elevationRaster.data}
  slopeRaster={slopeRaster.data}
  landcoverRaster={landcoverRaster.data}
  populationRaster={populationRaster.data}
  showElevation={showElevation}
  showSlope={showSlope}
  showLandcover={showLandcover}
  showPopulation={showPopulation}
  zones={zonesOk ? zones.data : undefined} showZones={zonesOk && showZones} highlight={highlight} resetKey={resetKey} grid={gridOk && showGrid ? grid.data : undefined} facilities={facOk && showFac ? fac.data : undefined}
              colorBy={colorBy} range={range} opacity={opacity} showWards={showWards} selectedWard={wardSel} onSelect={onSelect} />}
        </div>
        <div className="flex items-center gap-3 border-t border-line bg-panel px-3 py-1.5 text-[11px] text-sub" aria-label="Legend">
          {!gridOk && !zonesOk ? <span className="text-mute">No susceptibility layer yet — the map shows ward boundaries only. Risk highlighting appears once the pipeline has produced real scores.</span> :
            colorBy === "category" ? CATS.map((c) => <span key={c} className="flex items-center gap-1"><i className="inline-block h-2.5 w-2.5" style={{ background: CAT_COLORS[c] }} />{c}</span>) :
              (<><span className="num font-mono">{fmt(range[0], 2)}</span>
                <i className="h-2 w-40" style={{ background: `linear-gradient(90deg, ${[0, 0.2, 0.4, 0.6, 0.8, 1].map(rampColor).join(",")})` }} />
                <span className="num font-mono">{fmt(range[1], 2)}</span><span className="text-mute">{colorBy}</span></>)}
        </div>
      </div>
      <aside className="col-span-3 overflow-y-auto">
        <Panel title="Inspector">
          {!sel ? <p className="text-xs text-mute">Click a ward, grid cell or facility on the map.</p> : (
            <><div className="mb-2 text-[10px] uppercase tracking-widest text-cy">{sel.kind}</div>
              <table className="w-full"><tbody>{Object.entries(sel.props).filter(([k]) => k !== "tags_json").map(([k, v]) => (
                <tr key={k}><Td>{k}</Td><Td right mono>{typeof v === "number" ? fmt(v, 3) : String(v ?? "—")}</Td></tr>))}</tbody></table>
              {sel.kind === "cell" && <p className="mt-2 text-[10px] text-mute">Relative screening score within this run — not a flood probability.</p>}
              {sel.kind === "facility" && <p className="mt-2 text-[10px] text-mute">Located in a cell of this category; not necessarily flooded.</p>}</>)}
        </Panel>
      </aside>
    </div>
  );
}
