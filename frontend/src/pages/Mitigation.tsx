
import { useState } from "react";
import { Panel, Q, Stat, Th, Td, fmt } from "../components/ui";
import { useApi } from "../api";

const PROMPTS: Record<string, string> = {
  rel_elev_mean_m:
    "Field-verify local depressions and inlet/gully capacity in low-lying parts of the ward.",
  elev_mean_m:
    "Review the ward's position in its sub-catchment and downstream drainage outfalls.",
  slope_mean_deg:
    "Check outfall gradients and ponding at flat sections with the drainage department.",
  dist_waterway_m:
    "Inspect nearby stream/nallah channel condition, encroachment and culvert capacity.",
  builtup_share:
    "Identify opportunities to retain runoff through permeable surfaces and detention in dense built-up cells.",
};

type Ward = {
  ward_id: number;
  ward_name: string;
  score_mean: number | null;
  score_p90: number | null;
  high_share: number | null;
  exp_population_sum: number | null;
  exp_road_length_m: number | null;
  exp_n_hospital: number | null;
  exp_n_clinic: number | null;
  exp_n_school: number | null;
  exp_n_fire_station: number | null;
  exp_n_police: number | null;
  top_driver: string | null;
  rank_by_mean: number | null;
};

type SortKey =
  | "rank_by_mean"
  | "score_mean"
  | "score_p90"
  | "high_share"
  | "exp_population_sum"
  | "exp_road_length_m"
  | "exp_n_hospital"
  | "exp_n_school";

const DRIVER_LABELS: Record<string, string> = {
  rel_elev_mean_m: "Relative elevation",
  elev_mean_m: "Elevation",
  slope_mean_deg: "Slope",
  dist_waterway_m: "Distance to waterways",
  builtup_share: "Built-up share",
};

function numericValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : null;
}

export default function Mitigation() {
  const z = useApi<any>("/api/susceptibility/zones");
  const [search, setSearch] = useState("");
  const [driver, setDriver] = useState("all");
  const [shareFilter, setShareFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("rank_by_mean");
  const [ascending, setAscending] = useState(true);

  return (
    <div className="space-y-4">
      <div className="border-l-2 border-am bg-raise p-3 text-xs text-sub">
        <b className="text-text">Investigation priorities only.</b>{" "}
        Susceptibility and potential exposure are distinct indicators.
        These rankings are not flood probabilities, predicted impacts or
        engineering-certified recommendations. Verify priorities with
        local flood records, field inspections and drainage authorities.
      </div>

      <Q q={z} title="Prioritisation unavailable">
        {(d) => {
          const allRows: Ward[] = (d.features ?? [])
            .map((f: any) => f.properties as Ward)
            .filter((w: Ward) => w && w.ward_name);

          const validScores = allRows.filter(
            (w) => numericValue(w.score_mean) !== null
          );

          const topWard = [...validScores].sort(
            (a, b) => (b.score_mean ?? -Infinity) -
              (a.score_mean ?? -Infinity)
          )[0];

          const populationWard = [...allRows]
            .filter((w) => numericValue(w.exp_population_sum) !== null)
            .sort(
              (a, b) => (b.exp_population_sum ?? -Infinity) -
                (a.exp_population_sum ?? -Infinity)
            )[0];

          const highShareCount = validScores.filter(
            (w) => w.high_share !== null &&
              w.high_share !== undefined &&
              w.high_share >= 0.5
          ).length;

          const drivers = [...new Set(
            allRows.map((w) => w.top_driver).filter(
              (v): v is string => Boolean(v)
            )
          )].sort();

          const filteredRows = allRows
  .filter((w) => {
    if (!w.ward_name.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }

    if (driver !== "all" && w.top_driver !== driver) {
      return false;
    }

    if (
      shareFilter === "50" &&
      !(w.high_share != null && w.high_share >= 0.5)
    ) {
      return false;
    }

    if (
      shareFilter === "75" &&
      !(w.high_share != null && w.high_share >= 0.75)
    ) {
      return false;
    }

    if (shareFilter === "missing" && w.high_share != null) {
      return false;
    }

    return true;
  })
  .sort((a, b) => {
    const an = numericValue(a[sortKey]);
    const bn = numericValue(b[sortKey]);

    if (an === null && bn === null) {
      return a.ward_name.localeCompare(b.ward_name);
    }
    if (an === null) return 1;
    if (bn === null) return -1;

    const cmp = an - bn;
    return ascending ? cmp : -cmp;
  });

          const chooseSort = (key: SortKey) => {
            if (sortKey === key) {
              setAscending((v) => !v);
            } else {
              setSortKey(key);
              setAscending(key === "rank_by_mean");
            }
          };

          const sortButton = (label: string, key: SortKey) => (
            <button
              type="button"
              className="whitespace-nowrap hover:text-text"
              onClick={() => chooseSort(key)}
              title={`Sort by ${label}`}
            >
              {label}
              {sortKey === key ? (ascending ? " ↑" : " ↓") : ""}
            </button>
          );

          return (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Stat
                  label="Wards in dataset"
                  value={fmt(allRows.length, 0)}
                  sub={`${validScores.length} with susceptibility scores`}
                />
                <Stat
                  label="Highest mean score"
                  value={topWard ? fmt(topWard.score_mean, 2) : "—"}
                  sub={topWard?.ward_name ?? "No scored ward"}
                />
                <Stat
                  label="Highest modelled population exposure"
                  value={populationWard
                    ? fmt(populationWard.exp_population_sum, 0)
                    : "—"}
                  sub={populationWard?.ward_name ?? "No population data"}
                />
                <Stat
                  label="Wards with ≥50% high-category cells"
                  value={fmt(highShareCount, 0)}
                  sub="High + Very high share ≥50%"
                />
              </div>

              <Panel title="Filter and compare wards">
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                  <label className="text-xs text-sub">
                    Search ward
                    <input
                      className="mt-1 w-full border border-line bg-ink px-2 py-1.5 text-xs text-text"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Enter ward name..."
                    />
                  </label>

                  <label className="text-xs text-sub">
                    Dominant screening driver
                    <select
                      className="mt-1 w-full border border-line bg-ink px-2 py-1.5 text-xs text-text"
                      value={driver}
                      onChange={(e) => setDriver(e.target.value)}
                    >
                      <option value="all">All drivers</option>
                      {drivers.map((v) => (
                        <option key={v} value={v}>
                          {DRIVER_LABELS[v] ?? v}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="text-xs text-sub">
                    High + Very high cell share
                    <select
                      className="mt-1 w-full border border-line bg-ink px-2 py-1.5 text-xs text-text"
                      value={shareFilter}
                      onChange={(e) => setShareFilter(e.target.value)}
                    >
                      <option value="all">All wards</option>
                      <option value="50">At least 50%</option>
                      <option value="75">At least 75%</option>
                      <option value="missing">Missing share</option>
                    </select>
                  </label>
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-sub">
                  <span>
                    Showing {filteredRows.length} of {allRows.length} wards
                  </span>
                  <button
                    type="button"
                    className="border border-line px-2 py-1 hover:bg-raise"
                    onClick={() => {
                      setSearch("");
                      setDriver("all");
                      setShareFilter("all");
                      setSortKey("rank_by_mean");
                      setAscending(true);
                    }}
                  >
                    Reset filters
                  </button>
                </div>
              </Panel>

              <Panel title="Ward susceptibility and potential exposure">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[1250px]">
                    <thead>
                      <tr>
                        <Th>{sortButton("Rank", "rank_by_mean")}</Th>
                        <Th>Ward</Th>
                        <Th right>{sortButton("Mean score", "score_mean")}</Th>
                        <Th right>{sortButton("P90", "score_p90")}</Th>
                        <Th right>{sortButton("High share", "high_share")}</Th>
                        <Th right>{sortButton("Population*", "exp_population_sum")}</Th>
                        <Th right>{sortButton("Roads (km)*", "exp_road_length_m")}</Th>
                        <Th right>{sortButton("Hospitals*", "exp_n_hospital")}</Th>
                        <Th right>{sortButton("Schools*", "exp_n_school")}</Th>
                        <Th>Top driver</Th>
                        <Th>Investigation prompt</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRows.map((w) => (
                        <tr key={`${w.ward_id}-${w.ward_name}`}>
                          <Td mono>
                            {w.rank_by_mean == null ? "—" : fmt(w.rank_by_mean, 0)}
                          </Td>
                          <Td>{w.ward_name}</Td>
                          <Td right mono>{fmt(w.score_mean, 2)}</Td>
                          <Td right mono>{fmt(w.score_p90, 2)}</Td>
                          <Td right mono>
                            {w.high_share == null
                              ? "—"
                              : `${fmt(w.high_share * 100, 1)}%`}
                          </Td>
                          <Td right mono>{fmt(w.exp_population_sum, 0)}</Td>
                          <Td right mono>
                            {w.exp_road_length_m == null
                              ? "—"
                              : fmt(w.exp_road_length_m / 1000, 2)}
                          </Td>
                          <Td right mono>{fmt(w.exp_n_hospital, 0)}</Td>
                          <Td right mono>{fmt(w.exp_n_school, 0)}</Td>
                          <Td>
                            <span className="font-mono text-cy">
                              {w.top_driver
                                ? DRIVER_LABELS[w.top_driver] ?? w.top_driver
                                : "—"}
                            </span>
                          </Td>
                          <Td>
                            {w.top_driver
                              ? PROMPTS[w.top_driver] ??
                                "Investigate local drainage and flood history."
                              : "Driver unavailable; review underlying data."}
                          </Td>
                        </tr>
                      ))}
                      {filteredRows.length === 0 && (
                        <tr>
                          <td colSpan={11} className="p-4 text-center text-xs text-mute">
                            No wards match the current filters.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <p className="mt-3 text-[11px] text-mute">
                  * Population is modelled exposure, road length and facility
                  counts are mapped exposure indicators. Missing values are
                  shown as em dashes and are not treated as zero. Scores and
                  categories are relative to this study-area run.
                </p>
              </Panel>
            </div>
          );
        }}
      </Q>
    </div>
  );
}
