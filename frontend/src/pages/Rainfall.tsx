
import { useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel, Q, Stat, Unavailable, fmt } from "../components/ui";
import { useApi } from "../api";

function formatRainfallTime(value: string, aggregation: "hourly" | "daily") {
  const date = new Date(value.replace(" ", "T"));

  if (Number.isNaN(date.getTime())) return value;

  if (aggregation === "daily") {
    return date.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "2-digit",
      timeZone: "UTC",
    });
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

export default function Rainfall() {
  const [kind, setKind] = useState<"historical" | "forecast">("historical");
  const [agg, setAgg] = useState<"hourly" | "daily">("daily");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [acc, setAcc] = useState("acc_24h_mm");

  const invalidRange = Boolean(start && end && start > end);

  const qs = `kind=${kind}&agg=${agg}${start ? `&start=${start}` : ""}${end ? `&end=${end}` : ""}`;
  const sum = useApi<any>("/api/rainfall");
  const series = useApi<any>(
    invalidRange ? null as any : `/api/rainfall/series?${qs}`
  );

  const hasAcc = kind === "historical" && agg === "hourly";
    const rainfallRows = series.data?.data ?? [];

  const validRainfall = rainfallRows.filter(
    (row: any) =>
      row.precipitation_mm != null &&
      Number.isFinite(Number(row.precipitation_mm)) &&
      !(Number(row.missing) > 0)
  );

  const totalRainfall = validRainfall.reduce(
    (total: number, row: any) => total + Number(row.precipitation_mm),
    0
  );

  const maxRainfall = validRainfall.reduce(
    (maximum: number, row: any) =>
      Math.max(maximum, Number(row.precipitation_mm)),
    0
  );

  const hasMeasurableRain = validRainfall.some(
    (row: any) => Number(row.precipitation_mm) > 0
  );

  const rainfallUnit = agg === "daily" ? "mm/day" : "mm/hour";

  return (
    <div className="space-y-4">
      <Panel title="Source & provenance">
        <Q q={sum} title="Rainfall data not available">
          {(r) => (
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat
                label="Provider"
                value={<span className="text-sm">{r.provider}</span>}
                sub={r.kind}
              />
              <Stat
                label="Rows"
                value={fmt(r.rows, 0)}
                sub={`${r.missing_hours} missing hours`}
              />
              <Stat
                label="Range"
                value={
                  <span className="text-sm">
                    {r.start?.slice(0, 10)} → {r.end?.slice(0, 10)}
                  </span>
                }
                sub={r.timezone}
              />
              <Stat
                label="Retrieved"
                value={<span className="text-sm">{r.retrieved_at?.slice(0, 19)}</span>}
                sub="UTC"
              />
              <p className="col-span-full text-[11px] text-mute">
                {r.caveat} Weather data by Open-Meteo.com (CC BY 4.0).
              </p>
            </div>
          )}
        </Q>
      </Panel>

            <Panel title="Data freshness & coverage">
        <Q q={sum} title="Rainfall status unavailable">
          {(r) => {
            const items = [
              {
                label: "Historical rainfall",
                status: r.historical_status,
              },
              {
                label: "Forecast rainfall",
                status: r.forecast_status,
              },
            ];

            return (
              <div className="grid gap-3 sm:grid-cols-2">
                {items.map(({ label, status }) => (
                  <div
                    key={label}
                    className="border border-line p-3 space-y-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium">{label}</span>
                      <span className="text-xs uppercase tracking-wide">
                        {status?.freshness ?? "unknown"}
                      </span>
                    </div>

                    <div className="text-xs text-mute">
                      Coverage:{" "}
                      {status?.coverage_start?.slice(0, 10) ?? "Unavailable"}
                      {" — "}
                      {status?.coverage_end?.slice(0, 10) ?? "Unavailable"}
                    </div>

                    <div className="text-xs text-mute">
                      Local file updated:{" "}
                      {status?.file_updated_at
                        ? `${status.file_updated_at.replace("T", " ").slice(0, 19)} UTC`
                        : "Unavailable"}
                    </div>

                    <div className="text-xs text-mute">
                      {status?.rows ?? 0} records
                      {status?.age_hours != null
                        ? ` · ${status.age_hours} hours since file update`
                        : ""}
                    </div>
                  </div>
                ))}
                <p className="col-span-full text-xs text-mute">
                  Freshness is based on local file modification time, not the
                  provider's official forecast issue time. Historical coverage
                  dates describe the observations, not when they were retrieved.
                </p>
              </div>
            );
          }}
        </Q>
      </Panel>

      <Panel
        title="Precipitation"
        right={
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <select
              aria-label="Series kind"
              className="border border-line bg-ink px-2 py-1"
              value={kind}
              onChange={(e) => setKind(e.target.value as "historical" | "forecast")}
            >
              <option value="historical">Historical (reanalysis)</option>
              <option value="forecast">Forecast</option>
            </select>

            <select
              aria-label="Aggregation"
              className="border border-line bg-ink px-2 py-1"
              value={agg}
              onChange={(e) => setAgg(e.target.value as "hourly" | "daily")}
            >
              <option value="daily">Daily</option>
              <option value="hourly">Hourly</option>
            </select>

            <label className="flex items-center gap-1">
              <span>From date</span>
              <input
                aria-label="Start date"
                type="date"
                className="border border-line bg-ink px-2 py-1"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </label>

            <label className="flex items-center gap-1">
              <span>To date</span>
              <input
                aria-label="End date"
                type="date"
                className="border border-line bg-ink px-2 py-1"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </label>

            {(start || end) && (
              <button
                type="button"
                className="border border-line px-2 py-1 hover:bg-panel"
                onClick={() => {
                  setStart("");
                  setEnd("");
                }}
              >
                Clear dates
              </button>
            )}

            {hasAcc && (
              <select
                aria-label="Accumulation window"
                className="border border-line bg-ink px-2 py-1"
                value={acc}
                onChange={(e) => setAcc(e.target.value)}
              >
                {[
                  "acc_1h_mm",
                  "acc_3h_mm",
                  "acc_6h_mm",
                  "acc_12h_mm",
                  "acc_24h_mm",
                  "acc_72h_mm",
                ].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            )}
          </div>
        }
      >
        {invalidRange ? (
          <div role="alert" className="rounded border border-red-500/40 p-3 text-sm text-red-400">
            The start date must be on or before the end date. Please correct your date range.
          </div>
        ) : (
          <Q q={series} title={`${kind} rainfall unavailable`}>
            {(s) => (
              <>
                                <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="border border-line p-3">
                    <div className="text-xs text-mute">
                      Total rainfall in selected range
                    </div>
                    <div className="text-xl font-semibold">
                      {validRainfall.length
                        ? `${totalRainfall.toFixed(1)} mm`
                        : "—"}
                    </div>
                  </div>

                  <div className="border border-line p-3">
                    <div className="text-xs text-mute">
                      Maximum {agg === "daily" ? "daily" : "hourly"} rainfall
                    </div>
                    <div className="text-xl font-semibold">
                      {validRainfall.length
                        ? `${maxRainfall.toFixed(1)} mm`
                        : "—"}
                    </div>
                  </div>

                  <div className="border border-line p-3">
                    <div className="text-xs text-mute">
                      Rainfall observation status
                    </div>
                    <div className="text-sm font-semibold">
                      {!validRainfall.length
                        ? "No valid observations"
                        : hasMeasurableRain
                          ? "Measurable rainfall recorded"
                          : "No measurable rainfall in this range"}
                    </div>
                  </div>
                </div>

                <div className="mb-1 text-[11px] text-mute">
                  {kind === "forecast"
                    ? "MODEL FORECAST — not an official IMD warning."
                    : "HISTORICAL — gridded reanalysis, not gauge measurements."}{" "}
                  Gaps in the chart are missing data, not zero rainfall.
                  {start || end
                    ? ` Showing dates ${start || "from the earliest available date"} to ${end || "the latest available date"}.`
                    : " Showing all available dates."}
                </div>

                {s.data?.length === 0 ? (
                  <div className="p-6 text-center text-sm text-mute">
                    No rainfall records are available for this date range and data source.
                    Try another date range or clear the filters.
                  </div>
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer>
                      <ComposedChart data={s.data}>
                        <CartesianGrid stroke="#1e2b3b" />
                        <XAxis
                          dataKey="time"
                          tick={{ fill: "#7d8da1", fontSize: 10 }}
                          minTickGap={40}
                          tickFormatter={(t) => formatRainfallTime(String(t), agg)}
                        />
                        <YAxis
                          tick={{ fill: "#7d8da1", fontSize: 10 }}
                          label={{
                            value: "mm",
                            angle: -90,
                            fill: "#7d8da1",
                            fontSize: 10,
                          }}
                        />


                        <Tooltip
                          labelFormatter={(label) =>
                            `Date/time: ${formatRainfallTime(String(label), agg)} UTC`
                          }
                          formatter={(value: number | string, name: string) => {
                            const numericValue = Number(value);

                            if (!Number.isFinite(numericValue)) {
                              return [String(value), name];
                            }

                            const unit = name.startsWith("Precipitation")
                              ? `mm/${agg === "daily" ? "day" : "hour"}`
                              : "mm";

                            return [`${numericValue.toFixed(2)} ${unit}`, name];
                          }}
                          contentStyle={{
                            background: "#0f1722",
                            border: "1px solid #1e2b3b",
                            fontSize: 12,
                          }}
                        />
                        <Legend />
                        <Bar
                          dataKey="precipitation_mm"
                          name={`Precipitation (mm/${agg === "daily" ? "day" : "hour"})`}
                          fill={kind === "forecast" ? "#5b8def" : "#22d3ee"}
                        />
                        {hasAcc && (
                          <Line
                            dataKey={acc}
                            dot={false}
                            stroke="#f5a524"
                            name={`${acc} (trailing)`}
                            connectNulls={false}
                          />
                        )}
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
          </Q>
        )}
      </Panel>

      {sum.isError && (
        <Unavailable error={sum.error} title="Why this is empty" />
      )}
    </div>
  );
}
