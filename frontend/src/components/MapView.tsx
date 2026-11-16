import { useEffect, useRef } from "react";
import L from "leaflet";

export const CAT_COLORS: Record<string, string> = {
  "Very low": "#2b4c7e", Low: "#3f7cac", Moderate: "#e0b84a", High: "#f08a24", "Very high": "#e5484d",
};
const RAMP = ["#1d3557", "#2f6f9f", "#22d3ee", "#e0b84a", "#f08a24", "#e5484d"];
export function rampColor(t: number) {
  const x = Math.min(1, Math.max(0, t)) * (RAMP.length - 1);
  const i = Math.floor(x);
  return RAMP[Math.min(i + (x - i > 0.5 ? 1 : 0), RAMP.length - 1)];
}

export type MapProps = {
  
    elevationRaster?: any;
  slopeRaster?: any;
  landcoverRaster?: any;
  populationRaster?: any;
  showElevation?: boolean;
  showSlope?: boolean;
  showLandcover?: boolean;
  showPopulation?: boolean;
  waterways?: any;
  roads?: any;
  osmFacilities?: any;
  showWaterways?: boolean;
  showRoads?: boolean;
  showOsmFacilities?: boolean;

  wards?: any; grid?: any; facilities?: any; colorBy?: string; range?: [number, number]; opacity?: number;
  showWards?: boolean; zones?: any; showZones?: boolean; highlight?: boolean; resetKey?: number; selectedWard?: number | null; onSelect?: (kind: string, props: any) => void; height?: string; dim?: boolean;
};


export default function MapView({
  wards,
  grid,
  facilities,
  waterways,
  roads,
  osmFacilities,
  elevationRaster,
  slopeRaster,
  landcoverRaster,
  populationRaster,
  showElevation = false,
  showSlope = false,
  showLandcover = false,
  showPopulation = false,
  showWaterways = false,
  showRoads = false,
  showOsmFacilities = false,
  colorBy = "score",
  range,
  opacity = 0.7,
  showWards = true,
  zones,
  showZones = false,
  highlight = false,
  resetKey = 0,
  selectedWard,
  onSelect,
  height = "100%",
  dim
}: MapProps) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layers = useRef<{
  wards?: L.GeoJSON;
  grid?: L.GeoJSON;
  fac?: L.GeoJSON;
  zones?: L.GeoJSON;
  waterways?: L.GeoJSON;
  roads?: L.GeoJSON;
  osmFacilities?: L.GeoJSON;
  elevationRaster?: L.ImageOverlay;
  slopeRaster?: L.ImageOverlay;
  landcoverRaster?: L.ImageOverlay;
  populationRaster?: L.ImageOverlay;
}>({});
  const fitted = useRef(false);

  useEffect(() => {
    if (!el.current || map.current) return;
    const m = L.map(el.current, { zoomControl: true, preferCanvas: true }).setView([18.52, 73.86], 11);
    const rasterPane = m.createPane("rasterPane");
    rasterPane.style.zIndex = "350";
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors", maxZoom: 19,
    }).addTo(m);
    map.current = m;
    return () => { m.remove(); map.current = null; layers.current = {}; };
  }, []);

  useEffect(() => {
    const m = map.current; if (!m) return;
    layers.current.wards?.remove();
    if (wards && showWards) {
      layers.current.wards = L.geoJSON(wards, {
        style: (f: any) => ({ color: f?.properties?.ward_id === selectedWard ? "#22d3ee" : "#5b6f88", weight: f?.properties?.ward_id === selectedWard ? 2.5 : 0.8, fillOpacity: dim ? 0.05 : 0.02, fillColor: "#22d3ee" }),
        onEachFeature: (f, l) => { l.bindTooltip(String(f.properties.ward_name), { sticky: true }); l.on("click", () => onSelect?.("ward", f.properties)); },
      }).addTo(m);
      if (!fitted.current) { m.fitBounds(layers.current.wards.getBounds(), { padding: [10, 10] }); fitted.current = true; }
    }
  }, [wards, showWards, selectedWard, dim, onSelect]);

  useEffect(() => {
    const m = map.current; if (!m) return;
    layers.current.grid?.remove();
    if (grid?.features?.length) {
      const [lo, hi] = range ?? [0, 100];
      layers.current.grid = L.geoJSON(grid, {
        style: (f: any) => {
          const v = f?.properties?.[colorBy];
          const col = colorBy === "category" ? CAT_COLORS[v as string] : typeof v === "number" ? rampColor((v - lo) / (hi - lo || 1)) : "#444";
          const hot = v !== undefined && ["High", "Very high"].includes(f?.properties?.category);
          if (highlight) return { stroke: hot, color: f?.properties?.category === "Very high" ? "#ff3b3b" : "#ffa726", weight: 1.2, fillColor: col ?? "#444", fillOpacity: hot ? Math.min(1, opacity + 0.2) : 0.12 };
          return { stroke: false, fillColor: col ?? "#444", fillOpacity: opacity };
        },
        onEachFeature: (f, l) => l.on("click", () => onSelect?.("cell", f.properties)),
      }).addTo(m);
      layers.current.wards?.bringToFront();
    }
  }, [grid, colorBy, range, opacity, highlight, onSelect]);

  useEffect(() => {
    const m = map.current; if (!m) return;
    layers.current.zones?.remove();
    if (zones?.features?.length && showZones) {
      const sc = zones.features.map((f: any) => f.properties.score_mean).filter((x: any) => typeof x === "number");
      const lo = Math.min(...sc), hi = Math.max(...sc);
      layers.current.zones = L.geoJSON(zones, {
        style: (f: any) => {
          const p = f?.properties ?? {}; const top = highlight && p.rank_by_mean != null && p.rank_by_mean <= 10;
          return { color: top ? "#ff3b3b" : "#2a3a4f", weight: top ? 3 : 0.6, dashArray: top ? "6 3" : undefined, fillColor: typeof p.score_mean === "number" ? rampColor((p.score_mean - lo) / (hi - lo || 1)) : "#333", fillOpacity: typeof p.score_mean === "number" ? opacity * 0.85 : 0.05 };
        },
        onEachFeature: (f, l) => { const p = f.properties; l.bindTooltip(`${p.ward_name}${p.rank_by_mean != null ? ` · rank ${p.rank_by_mean} · mean score ${Number(p.score_mean).toFixed(1)}` : ""}`, { sticky: true }); l.on("click", () => onSelect?.("ward", p)); },
      }).addTo(m);
      layers.current.zones.bringToBack();
      layers.current.wards?.bringToFront();
    }
  }, [zones, showZones, highlight, opacity, onSelect]);

  useEffect(() => {
    if (resetKey && map.current && layers.current.wards) map.current.fitBounds(layers.current.wards.getBounds(), { padding: [10, 10] });
  }, [resetKey]);

  useEffect(() => {
    const m = map.current; if (!m) return;
    layers.current.fac?.remove();
    if (facilities?.features?.length) {
      layers.current.fac = L.geoJSON(facilities, {
        pointToLayer: (_f, ll) => L.circleMarker(ll, { radius: 4, color: "#0a0f16", weight: 1, fillColor: "#22d3ee", fillOpacity: 0.95 }),
        onEachFeature: (f, l) => { l.bindTooltip(`${f.properties.amenity}${f.properties.name ? ": " + f.properties.name : ""}`); l.on("click", () => onSelect?.("facility", f.properties)); },
      }).addTo(m);
    }
  }, [facilities, onSelect]);

  
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    layers.current.waterways?.remove();
    if (showWaterways && waterways?.features?.length) {
      layers.current.waterways = L.geoJSON(waterways, {
        style: { color: "#38bdf8", weight: 2, opacity: 0.9 },
        onEachFeature: (f, l) => {
          if (f.properties?.name) l.bindTooltip(String(f.properties.name));
          l.on("click", () => onSelect?.("waterway", f.properties));
        },
      }).addTo(m);
    }
  }, [waterways, showWaterways, onSelect]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    layers.current.roads?.remove();
    if (showRoads && roads?.features?.length) {
      layers.current.roads = L.geoJSON(roads, {
        style: { color: "#fbbf24", weight: 1, opacity: 0.7 },
        onEachFeature: (f, l) => {
          if (f.properties?.name) l.bindTooltip(String(f.properties.name));
          l.on("click", () => onSelect?.("road", f.properties));
        },
      }).addTo(m);
    }
  }, [roads, showRoads, onSelect]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    layers.current.osmFacilities?.remove();
    if (showOsmFacilities && osmFacilities?.features?.length) {
      layers.current.osmFacilities = L.geoJSON(osmFacilities, {
        pointToLayer: (_f, ll) =>
          L.circleMarker(ll, {
            radius: 3,
            color: "#111827",
            weight: 1,
            fillColor: "#a78bfa",
            fillOpacity: 0.9,
          }),
        onEachFeature: (f, l) => {
          if (f.properties?.name) l.bindTooltip(String(f.properties.name));
          l.on("click", () => onSelect?.("osm facility", f.properties));
        },
      }).addTo(m);
    }
  }, [osmFacilities, showOsmFacilities, onSelect]);

  useEffect(() => {
    if (selectedWard == null || !layers.current.wards || !map.current) return;
    layers.current.wards.eachLayer((l: any) => { if (l.feature?.properties?.ward_id === selectedWard) map.current!.fitBounds(l.getBounds(), { padding: [30, 30], maxZoom: 14 }); });
  }, [selectedWard]);

    useEffect(() => {
    const m = map.current;
    layers.current.elevationRaster?.remove();
    if (!m || !showElevation || !elevationRaster?.image || !elevationRaster?.bounds) return;

    layers.current.elevationRaster = L.imageOverlay(
      elevationRaster.image,
      elevationRaster.bounds,
      { pane: "rasterPane", opacity: 0.75, interactive: false }
    ).addTo(m);
  }, [elevationRaster, showElevation]);

  useEffect(() => {
    const m = map.current;
    layers.current.slopeRaster?.remove();
    if (!m || !showSlope || !slopeRaster?.image || !slopeRaster?.bounds) return;

    layers.current.slopeRaster = L.imageOverlay(
      slopeRaster.image,
      slopeRaster.bounds,
      { pane: "rasterPane", opacity: 0.75, interactive: false }
    ).addTo(m);
  }, [slopeRaster, showSlope]);

  useEffect(() => {
    const m = map.current;
    layers.current.landcoverRaster?.remove();
    if (!m || !showLandcover || !landcoverRaster?.image || !landcoverRaster?.bounds) return;

    layers.current.landcoverRaster = L.imageOverlay(
      landcoverRaster.image,
      landcoverRaster.bounds,
      { pane: "rasterPane", opacity: 0.75, interactive: false }
    ).addTo(m);
  }, [landcoverRaster, showLandcover]);

  useEffect(() => {
    const m = map.current;
    layers.current.populationRaster?.remove();
    if (!m || !showPopulation || !populationRaster?.image || !populationRaster?.bounds) return;

    layers.current.populationRaster = L.imageOverlay(
      populationRaster.image,
      populationRaster.bounds,
      { pane: "rasterPane", opacity: 0.75, interactive: false }
    ).addTo(m);
  }, [populationRaster, showPopulation]);

  return <div ref={el} style={{ height, width: "100%" }} role="application" aria-label="Interactive map of Pune" data-testid="map" />;
}
