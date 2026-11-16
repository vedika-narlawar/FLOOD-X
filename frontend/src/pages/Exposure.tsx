
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ScatterChart,
  Scatter,
  ZAxis,
} from "recharts";
import { Panel, Q, Unavailable, fmt } from "../components/ui";
import { useApi } from "../api";

const ASSETS = [
  "n_hospital",
  "n_clinic",
  "n_school",
  "n_fire_station",
  "n_police",
];

const tip = {
  contentStyle: {
    background: "#0f1722",
    border: "1px solid #1e2b3b",
    fontSize: 12,
  },
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
  contrib_mean_rel_elev_mean_m: number | null;
  contrib_mean_elev_mean_m: number | null;
  contrib_mean_slope_mean_deg: number | null;
  contrib_mean_dist_waterway_m: number | null;
  contrib_mean_builtup_share: number | null;
  top_driver: string | null;
  rank_by_mean: number | null;
};

const DRIVER_LABELS: Record<string, string> = {
  rel_elev_mean_m: "Relative elevation",
  elev_mean_m: "Elevation",
  slope_mean_deg: "Slope",
  dist_waterway_m: "Distance to waterways",
  builtup_share: "Built-up share",
};

const CONTRIBUTION_FACTORS = [
  {
    key: "contrib_mean_rel_elev_mean_m",
    label: "Relative elevation",
    color: "#22d3ee",
  },
  {
    key: "contrib_mean_elev_mean_m",
    label: "Absolute elevation",
    color: "#5b8def",
  },
  {
    key: "contrib_mean_slope_mean_deg",
    label: "Slope",
    color: "#f5a524",
  },
  {
    key: "contrib_mean_dist_waterway_m",
    label: "Distance to waterways",
    color: "#ef5350",
  },
  {
    key: "contrib_mean_builtup_share",
    label: "Built-up share",
    color: "#3ecf8e",
  },
] as const;

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : null;
}

export default function Exposure() {
  const [asset, setAsset] = useState("all");
  const [shareFilter, setShareFilter] = useState("all");
  const [driverFilter, setDriverFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedWard, setSelectedWard] = useState<Ward | null>(null);

  const ex = useApi<any>("/api/exposure/summary");
  const zones = useApi<any>("/api/susceptibility/zones");

  return (
    <div className="space-y-4">
      <Panel title="Interpretation and limitations">
        <p className="text-xs text-sub">
          Assets listed below are potentially exposed to susceptibility:
          they are located in grid cells assigned a relative screening
          category. They are not necessarily flooded. Exposure is not
          predicted damage, loss, or flood probability.
        </p>
      </Panel>

      {/* Existing descriptive exposure charts */}
      <Q q={ex} title="Exposure analysis unavailable">
        {(e) => {
          const f = e.sections.facilities;
          const r = e.sections.roads;
          const p = e.sections.population;
          const cats: string[] = e.categories;
          const shown = asset === "all" ? ASSETS : [asset];

          const fdata =
            f.status === "available"
              ? cats.map((c) => ({
                  c,
                  ...Object.fromEntries(
                    shown.map((a) => [
                      a,
                      f.by_category[c]?.[a] ?? 0,
                    ]),
                  ),
                }))
              : [];

          return (
            <div className="grid grid-cols-12 gap-4">
              <Panel
                title="Facilities by susceptibility category"
                className="col-span-12 lg:col-span-6"
                right={
                  <select
                    aria-label="Asset type"
                    className="border border-line bg-ink px-1 text-xs"
                    value={asset}
                    onChange={(ev) => setAsset(ev.target.value)}
                  >
                    <option value="all">All assets</option>
                    {ASSETS.map((a) => (
                      <option key={a} value={a}>
                        {a.replace("n_", "")}
                      </option>
                    ))}
                  </select>
                }
              >
                {f.status !== "available" ? (
                  <Unavailable
                    error={{
                      message: f.reason,
                      detail: { reason: f.reason },
                    }}
                  />
                ) : (
                  <>
                    <div className="h-64">
                      <ResponsiveContainer>
                        <BarChart data={fdata}>
                          <CartesianGrid stroke="#1e2b3b" />
                          <XAxis
                            dataKey="c"
                            tick={{ fill: "#a9b6c6", fontSize: 10 }}
                          />
                          <YAxis
                            allowDecimals={false}
                            tick={{ fill: "#7d8da1", fontSize: 10 }}
                          />
                          <Tooltip {...tip} />
                          <Legend />
                          {shown.map((a, i) => (
                            <Bar
                              key={a}
                              dataKey={a}
                              stackId="a"
                              name={a.replace("n_", "")}
                              fill={
                                [
                                  "#22d3ee",
                                  "#5b8def",
                                  "#f5a524",
                                  "#ef5350",
                                  "#3ecf8e",
                                ][i]
                              }
                            />
                          ))}
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="text-[11px] text-mute">{f.note}</p>
                  </>
                )}
              </Panel>

              <Panel
                title="Mapped road length (km)"
                className="col-span-12 lg:col-span-6"
              >
                {r.status !== "available" ? (
                  <Unavailable
                    error={{
                      message: r.reason,
                      detail: { reason: r.reason },
                    }}
                  />
                ) : (
                  <div className="h-64">
                    <ResponsiveContainer>
                      <BarChart
                        data={cats.map((c) => ({
                          c,
                          km: r.by_category[c],
                        }))}
                      >
                        <CartesianGrid stroke="#1e2b3b" />
                        <XAxis
                          dataKey="c"
                          tick={{ fill: "#a9b6c6", fontSize: 10 }}
                        />
                        <YAxis
                          tick={{ fill: "#7d8da1", fontSize: 10 }}
                        />
                        <Tooltip {...tip} />
                        <Bar dataKey="km" fill="#5b8def" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Panel>

              <Panel
                title={`Population by susceptibility category · ${p.unit ?? ""}`}
                className="col-span-12"
              >
                {p.status !== "available" ? (
                  <Unavailable
                    error={{
                      message: p.reason,
                      detail: { reason: p.reason },
                    }}
                  />
                ) : (
                  <>
                    <div className="h-56">
                      <ResponsiveContainer>
                        <BarChart
                          data={cats.map((c) => ({
                            c,
                            pop: p.by_category[c],
                          }))}
                        >
                          <CartesianGrid stroke="#1e2b3b" />
                          <XAxis
                            dataKey="c"
                            tick={{ fill: "#a9b6c6", fontSize: 10 }}
                          />
                          <YAxis
                            tick={{ fill: "#7d8da1", fontSize: 10 }}
                          />
                          <Tooltip {...tip} />
                          <Bar dataKey="pop" fill="#f5a524" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="text-[11px] text-mute">
                      Total {fmt(p.total, 0)} people. Population is modelled
                      WorldPop data, not a census. Results depend on raster
                      resolution and the analysis grid.
                    </p>
                  </>
                )}
              </Panel>
            </div>
          );
        }}
      </Q>

      {/* New ward-level susceptibility versus exposure analysis */}
      <Q q={zones} title="Ward-level analysis unavailable">
        {(d) => {
          const allRows: Ward[] = (d.features ?? [])
            .map((f: any) => f.properties as Ward)
            .filter((row: Ward) => row.ward_name !== "PCMC: 64, Zone C_1" && row.ward_name !== "PCMC: 58, Zone C_2")
            .filter(
              (w: Ward) =>
                w &&
                typeof w.ward_name === "string" &&
                numberOrNull(w.score_mean) !== null &&
                numberOrNull(w.exp_population_sum) !== null,
            );

          const drivers = [
            ...new Set(
              allRows
                .map((w) => w.top_driver)
                .filter((v): v is string => Boolean(v)),
            ),
          ].sort();

          const filteredRows = allRows
            .filter((w) => {
              if (
                !w.ward_name
                  .toLowerCase()
                  .includes(search.toLowerCase().trim())
              ) {
                return false;
              }

              if (
                driverFilter !== "all" &&
                w.top_driver !== driverFilter
              ) {
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

              return true;
            })
            .sort(
              (a, b) =>
                (b.score_mean ?? -Infinity) -
                (a.score_mean ?? -Infinity),
            );

          const populationRanked = [...filteredRows].sort(
            (a, b) =>
              (b.exp_population_sum ?? -Infinity) -
              (a.exp_population_sum ?? -Infinity),
          );

          const highBoth = filteredRows.filter(
            (w) =>
              w.score_mean != null &&
              w.score_mean >= 60 &&
              w.exp_population_sum != null &&
              w.exp_population_sum >=
                (allRows.length
                  ? allRows.reduce(
                      (sum, x) =>
                        sum + (x.exp_population_sum ?? 0),
                      0,
                    ) / allRows.length
                  : Infinity),
          );

          const selected =
            selectedWard &&
            filteredRows.find(
              (w) =>
                w.ward_id === selectedWard.ward_id &&
                w.ward_name === selectedWard.ward_name,
            );

            const contributionData = selected
              ? CONTRIBUTION_FACTORS.map((factor) => ({
                  factor: factor.label,
                  points: numberOrNull(selected[factor.key]) ?? 0,
                  color: factor.color,
                }))
              : [];

            const averagePopulation =
              allRows.length > 0
                ? allRows.reduce(
                    (sum, ward) => sum + (ward.exp_population_sum ?? 0),
                    0,
                  ) / allRows.length
                : null;

            const recommendations = selected
              ? [
                  ...(selected.score_mean != null && selected.score_mean >= 70
                    ? [
                        {
                          title: "Investigate terrain and drainage",
                          reason:
                            "The ward's mean screening score is at least 70. Check local terrain, drainage pathways, and historical flood records.",
                        },
                      ]
                    : selected.score_mean != null && selected.score_mean >= 60
                      ? [
                          {
                            title: "Verify local susceptibility indicators",
                            reason:
                              "The ward's mean screening score is at least 60. Examine the contributing terrain and waterway factors.",
                          },
                        ]
                      : []),

                  ...(selected.high_share != null && selected.high_share >= 0.5
                    ? [
                        {
                          title: "Inspect higher-scoring grid cells",
                          reason:
                            "At least 50% of scored cells fall in the High or Very high categories. Verify these locations against local evidence.",
                        },
                      ]
                    : []),

                  ...(averagePopulation != null &&
                  selected.exp_population_sum != null &&
                  selected.exp_population_sum >= averagePopulation
                    ? [
                        {
                          title: "Review population exposure",
                          reason:
                            "Modelled population exposure is at or above the study-area ward mean. Verify settlement locations and potentially affected populations.",
                        },
                      ]
                    : []),

                  ...(selected.exp_road_length_m != null &&
                  selected.exp_road_length_m > 0
                    ? [
                        {
                          title: "Verify road and drainage conditions",
                          reason:
                            "Mapped roads are present in the ward. Check known waterlogging locations, drainage conditions, and emergency access routes.",
                        },
                      ]
                    : []),

                  ...([
                    selected.exp_n_hospital,
                    selected.exp_n_school,
                    selected.exp_n_fire_station,
                  ].some((count) => count != null && count > 0)
                    ? [
                        {
                          title: "Verify critical-facility access",
                          reason:
                            "Mapped critical facilities are present. Verify their locations and access routes; mapped presence does not establish flood exposure.",
                        },
                      ]
                    : []),
                ]
              : [];

          return (
            <div className="space-y-4">
              <Panel title="Susceptibility vs population exposure">
                <p className="mb-3 text-xs text-sub">
                  Each point represents a ward. The horizontal axis shows
                  mean susceptibility score; the vertical axis shows
                  modelled population exposure. Use the plot to explore
                  wards with different combinations of these indicators.
                  The score threshold of 60 and mean population exposure
                  are exploratory reference points, not validated risk
                  thresholds.
                </p>

                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                  <label className="text-xs text-sub">
                    Search ward
                    <input
                      className="mt-1 w-full border border-line bg-ink px-2 py-1.5 text-xs text-text"
                      value={search}
                      onChange={(ev) => setSearch(ev.target.value)}
                      placeholder="Enter ward name..."
                    />
                  </label>

                  <label className="text-xs text-sub">
                    Dominant screening driver
                    <select
                      className="mt-1 w-full border border-line bg-ink px-2 py-1.5 text-xs text-text"
                      value={driverFilter}
                      onChange={(ev) => setDriverFilter(ev.target.value)}
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
                      onChange={(ev) => setShareFilter(ev.target.value)}
                    >
                      <option value="all">All wards</option>
                      <option value="50">At least 50%</option>
                      <option value="75">At least 75%</option>
                    </select>
                  </label>
                </div>

                <div className="mt-2 text-xs text-sub">
                  Showing {filteredRows.length} of {allRows.length} wards
                  with both score and population data.
                </div>

                <div className="mt-3 h-80">
                  <ResponsiveContainer>
                    <ScatterChart margin={{ top: 12, right: 24, bottom: 24, left: 16 }}>
                      <CartesianGrid stroke="#1e2b3b" />
                      <XAxis
                        type="number"
                        dataKey="score_mean"
                        name="Mean susceptibility score"
                        domain={[0, 100]}
                        tick={{ fill: "#a9b6c6", fontSize: 10 }}
                        label={{
                          value: "Mean susceptibility score (0–100)",
                          position: "insideBottom",
                          offset: -12,
                          fill: "#a9b6c6",
                          fontSize: 11,
                        }}
                      />
                      <YAxis
                        type="number"
                        dataKey="exp_population_sum"
                        name="Modelled population exposure"
                        tick={{ fill: "#a9b6c6", fontSize: 10 }}
                        tickFormatter={(v) => Number(v).toLocaleString("en-IN")}
                        width={85}
                      />
                      <ZAxis range={[55, 55]} />
                      <Tooltip
                        {...tip}
                        cursor={{ strokeDasharray: "3 3" }}
                        formatter={(value: any, name: any) => [
                          name === "Mean susceptibility score"
                            ? fmt(Number(value), 2)
                            : fmt(Number(value), 0),
                          name,
                        ]}
                        labelFormatter={(_, payload) =>
                          payload?.[0]?.payload?.ward_name ?? "Ward"
                        }
                      />
                      <Scatter
                        name="Wards"
                        data={filteredRows}
                        fill="#22d3ee"
                        fillOpacity={0.8}
                        onClick={(point: any) => {
                          const row = point?.payload ?? point;
                          if (row?.ward_name) setSelectedWard(row);
                        }}
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-[11px] text-mute">
                  Select a point to inspect its ward. A ward with a high
                  screening score and high modelled population exposure
                  merits investigation; this does not establish actual
                  flooding or predicted damage.
                </p>
              </Panel>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <Panel title="Wards matching current filters">
                  <p className="text-2xl font-semibold">
                    {filteredRows.length}
                  </p>
                  <p className="mt-1 text-xs text-sub">
                    Wards with available susceptibility and population
                    values.
                  </p>
                </Panel>

                <Panel title="High score and above-average exposure">
                  <p className="text-2xl font-semibold">{highBoth.length}</p>
                  <p className="mt-1 text-xs text-sub">
                    Exploratory count using score ≥60 and population
                    exposure at or above the study-area mean.
                  </p>
                </Panel>

                <Panel title="Highest population exposure">
                  <p className="text-sm font-semibold">
                    {populationRanked[0]?.ward_name ?? "No matching ward"}
                  </p>
                  <p className="mt-1 text-xs text-sub">
                    {populationRanked[0]
                      ? `${fmt(populationRanked[0].exp_population_sum, 0)} modelled people`
                      : "Adjust the filters to see matching wards."}
                  </p>
                </Panel>
              </div>

              {selected && (
                <Panel
                  title={`Selected ward · ${selected.ward_name}`}
                  right={
                    <button
                      type="button"
                      className="border border-line px-2 py-1 text-xs hover:bg-raise"
                      onClick={() => setSelectedWard(null)}
                    >
                      Clear selection
                    </button>
                  }
                >
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    <div>
                      <p className="text-xs text-sub">Mean score</p>
                      <p className="text-lg font-semibold">
                        {fmt(selected.score_mean, 2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-sub">P90 score</p>
                      <p className="text-lg font-semibold">
                        {fmt(selected.score_p90, 2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-sub">High-category share</p>
                      <p className="text-lg font-semibold">
                        {selected.high_share == null
                          ? "—"
                          : `${fmt(selected.high_share * 100, 1)}%`}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-sub">Modelled population</p>
                      <p className="text-lg font-semibold">
                        {fmt(selected.exp_population_sum, 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-sub">Mapped roads</p>
                      <p className="text-lg font-semibold">
                        {selected.exp_road_length_m == null
                          ? "—"
                          : `${fmt(selected.exp_road_length_m / 1000, 2)} km`}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-sub">Hospitals</p>
                      <p className="text-lg font-semibold">
                        {fmt(selected.exp_n_hospital, 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-sub">Schools</p>
                      <p className="text-lg font-semibold">
                        {fmt(selected.exp_n_school, 0)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-sub">Dominant driver</p>
                      <p className="text-sm font-semibold">
                        {selected.top_driver
                          ? DRIVER_LABELS[selected.top_driver] ??
                            selected.top_driver
                          : "—"}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 border-t border-line pt-3">
                    <h3 className="text-sm font-semibold">
                      Recommended investigations
                    </h3>

                    <p className="mt-1 text-xs text-sub">
                      These suggestions use transparent screening thresholds
                      and mapped indicators. They are not validated predictions
                      of flooding or intervention effectiveness.
                    </p>

                    {recommendations.length > 0 ? (
                      <div className="mt-3 space-y-3">
                        {recommendations.map((item) => (
                          <div
                            key={item.title}
                            className="border-l-2 border-cyan-400 pl-3"
                          >
                            <p className="text-sm font-medium">{item.title}</p>
                            <p className="mt-1 text-xs text-sub">
                              {item.reason}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-sub">
                        No additional investigation triggers were met by the
                        available indicators. This does not establish that the
                        ward is free from flood-related concerns. Review local
                        records and check for missing data.
                      </p>
                    )}
                  </div>
                </Panel>
              )}

              {selected && (
              <Panel title={`Why this score? · ${selected.ward_name}`}>
                <p className="mb-3 text-xs text-sub">
                  These bars show the average contribution of each model factor
                  to this ward's mean relative susceptibility screening score.
                  Values are score points, not probabilities or percentages of
                  actual flood risk.
                </p>

                <div className="h-72">
                  <ResponsiveContainer>
                    <BarChart
                      data={contributionData}
                      layout="vertical"
                      margin={{ top: 4, right: 24, bottom: 4, left: 16 }}
                    >
                      <CartesianGrid stroke="#1e2b3b" horizontal={false} />
                      <XAxis
                        type="number"
                        domain={[0, "auto"]}
                        tick={{ fill: "#a9b6c6", fontSize: 10 }}
                        label={{
                          value: "Contribution to score (points)",
                          position: "insideBottom",
                          offset: -2,
                          fill: "#a9b6c6",
                          fontSize: 10,
                        }}
                      />
                      <YAxis
                        type="category"
                        dataKey="factor"
                        width={150}
                        tick={{ fill: "#a9b6c6", fontSize: 10 }}
                      />
                      <Tooltip
                        {...tip}
                        formatter={(value: number) => [
                          `${fmt(value, 2)} points`,
                          "Mean contribution",
                        ]}
                      />
                      <Bar
                        dataKey="points"
                        name="Mean contribution"
                        fill="#22d3ee"
                        radius={[0, 3, 3, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="mt-3 space-y-1 text-xs text-sub">
                  {contributionData
                    .slice()
                    .sort((a, b) => b.points - a.points)
                    .map((factor) => (
                      <div
                        key={factor.factor}
                        className="flex items-center justify-between gap-3"
                      >
                        <span>{factor.factor}</span>
                        <span className="font-medium text-text">
                          {fmt(factor.points, 2)} points
                        </span>
                      </div>
                    ))}
                </div>

                <p className="mt-3 text-[11px] text-mute">
                  Contributions follow the configured expert-judgement weights,
                  normalization, and available-input rules. The largest contribution
                  identifies the strongest contributor under this index, not a
                  proven cause of flooding. Scores are relative screening indicators,
                  not calibrated flood probabilities.
                </p>
              </Panel>
            )}

              <Panel title="Ward comparison and investigation list">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[850px] text-xs">
                    <thead>
                      <tr className="border-b border-line text-left text-sub">
                        <th className="p-2">Ward</th>
                        <th className="p-2 text-right">Mean score</th>
                        <th className="p-2 text-right">High share</th>
                        <th className="p-2 text-right">Population*</th>
                        <th className="p-2 text-right">Roads (km)*</th>
                        <th className="p-2">Dominant driver</th>
                        <th className="p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {populationRanked.slice(0, 20).map((w) => (
                        <tr
                          key={`${w.ward_id}-${w.ward_name}`}
                          className="border-b border-line/60"
                        >
                          <td className="p-2">{w.ward_name}</td>
                          <td className="p-2 text-right">
                            {fmt(w.score_mean, 2)}
                          </td>
                          <td className="p-2 text-right">
                            {w.high_share == null
                              ? "—"
                              : `${fmt(w.high_share * 100, 1)}%`}
                          </td>
                          <td className="p-2 text-right">
                            {fmt(w.exp_population_sum, 0)}
                          </td>
                          <td className="p-2 text-right">
                            {w.exp_road_length_m == null
                              ? "—"
                              : fmt(w.exp_road_length_m / 1000, 2)}
                          </td>
                          <td className="p-2">
                            {w.top_driver
                              ? DRIVER_LABELS[w.top_driver] ?? w.top_driver
                              : "—"}
                          </td>
                          <td className="p-2">
                            <button
                              type="button"
                              className="border border-line px-2 py-1 hover:bg-raise"
                              onClick={() => setSelectedWard(w)}
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      ))}
                      {populationRanked.length === 0 && (
                        <tr>
                          <td
                            colSpan={7}
                            className="p-4 text-center text-sub"
                          >
                            No wards match the current filters.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-[11px] text-mute">
                  * Population is modelled exposure. Road length and
                  facility counts are mapped indicators, not confirmed
                  flood impacts. The list is ordered by modelled
                  population exposure, not by a validated flood-risk score.
                </p>
              </Panel>
            </div>
          );
        }}
      </Q>
    </div>
  );
}
