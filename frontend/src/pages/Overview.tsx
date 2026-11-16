
import { Badge, Panel, Q, Stat, fmt } from "../components/ui";
import MapView from "../components/MapView";
import { useApi } from "../api";

const HIGH_CATEGORIES = ["High", "Very high"];

export default function Overview() {
  const meta = useApi<any>("/api/metadata");
  const status = useApi<any>("/api/status");
  const wards = useApi<any>("/api/boundaries/wards");
  const zones = useApi<any>("/api/susceptibility/zones");
  const pipe = useApi<any>("/api/pipeline/status");
  const rain = useApi<any>("/api/rainfall");
  const exp = useApi<any>("/api/exposure/summary");

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 border-l-2 border-cy bg-raise p-3 text-xs text-sub">
        <b className="text-text">Scope.</b> FLOOD-X screens{" "}
        <i>relative physical flood susceptibility</i> and{" "}
        <i>potential exposure</i> for Pune. It does not produce validated
        flood probabilities, flood depths, predictions or warnings.
      </div>

      <div className="col-span-12 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Q q={meta}>
          {(m) => (
            <>
              <Stat
                label="Study area"
                value={fmt(m.study_area?.area_km2)}
                unit="km²"
                sub={m.study_area?.analysis_crs}
              />
              <Stat
                label="Wards (PMC + PCMC)"
                value={fmt(m.study_area?.n_wards, 0)}
                sub="DataMeet boundaries"
              />
            </>
          )}
        </Q>

        <Q q={status}>
          {(s) => (
            <>
              <Stat
                label="Datasets ready"
                value={`${s.datasets_by_status.ready_for_analysis ?? 0}`}
                sub={`${Object.values(s.datasets_by_status).reduce(
                  (a: any, b: any) => a + b,
                  0
                )} registered`}
              />
              <Stat
                label="Stages OK"
                value={`${s.stages_by_status.success ?? 0}`}
                sub={`${s.stages_by_status.blocked ?? 0} blocked · ${
                  s.stages_by_status.failed ?? 0
                } failed`}
              />
              <Stat
                label="Susceptibility layer"
                value={s.susceptibility_available ? "Available" : "Not generated"}
              />
            </>
          )}
        </Q>
      </div>

      <Panel title="Potential exposure at a glance" className="col-span-12">
        <Q q={exp} title="Exposure metrics unavailable">
          {(e) => {
            const p = e.sections?.population;
            const r = e.sections?.roads;

            const populationAvailable =
              p?.status === "available" &&
              HIGH_CATEGORIES.every((c) => Number.isFinite(p.by_category?.[c]));

            const roadsAvailable =
              r?.status === "available" &&
              HIGH_CATEGORIES.every((c) => Number.isFinite(r.by_category?.[c]));

            const highPopulation = populationAvailable
              ? HIGH_CATEGORIES.reduce((sum, c) => sum + p.by_category[c], 0)
              : null;

            const totalPopulation = populationAvailable
              ? Number(p.total)
              : null;

            const highPopulationShare =
              highPopulation !== null &&
              totalPopulation !== null &&
              totalPopulation > 0
                ? (highPopulation / totalPopulation) * 100
                : null;

            const highRoadKm = roadsAvailable
              ? HIGH_CATEGORIES.reduce((sum, c) => sum + r.by_category[c], 0)
              : null;

            return (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <Stat
                    label="Population in High + Very high"
                    value={highPopulation === null ? "—" : fmt(highPopulation, 0)}
                    sub="Modelled people in these categories"
                  />
                  <Stat
                    label="Share of modelled population"
                    value={highPopulationShare === null
                      ? "—"
                      : `${highPopulationShare.toFixed(1)}%`}
                    sub="Of the reported population total"
                  />
                  <Stat
                    label="Roads in High + Very high"
                    value={highRoadKm === null ? "—" : fmt(highRoadKm, 1)}
                    unit="km"
                    sub="Mapped road length"
                  />
                  <Q q={zones} title="Ward ranking unavailable">
                    {(z) => {
                      const ranked = (z.features ?? [])
                        .map((f: any) => f.properties)
                        .filter((w: any) => Number.isFinite(w.score_mean))
                        .sort(
                          (a: any, b: any) =>
                            (a.rank_by_mean ?? Infinity) -
                            (b.rank_by_mean ?? Infinity)
                        );

                      const top = ranked[0];

                      return (
                        <Stat
                          label="Highest mean susceptibility"
                          value={top ? fmt(top.score_mean, 2) : "—"}
                          sub={top?.ward_name ?? "No ranked ward available"}
                        />
                      );
                    }}
                  </Q>
                </div>

                <div className="border-l-2 border-cy bg-raise p-3 text-xs text-sub">
                  <b className="text-text">What these figures mean.</b>{" "}
                  They identify modelled population and mapped road length
                  located in relatively higher-susceptibility categories.
                  They do not estimate actual flood impacts, damage or loss.
                  Population figures use WorldPop modelled data; mapped roads
                  depend on OpenStreetMap completeness.
                </div>

                {e.caveat && (
                  <p className="text-[11px] text-mute">{e.caveat}</p>
                )}
              </div>
            );
          }}
        </Q>
      </Panel>

      <Panel title="Study area" className="col-span-12 lg:col-span-7">
        <div className="h-[420px]">
          <Q q={wards}>{(w) => <MapView wards={w} />}</Q>
        </div>
      </Panel>

      <div className="col-span-12 space-y-4 lg:col-span-5">
        <Panel title="Rainfall context">
          <Q q={rain} title="Rainfall unavailable">
            {(r) => (
              <div className="text-xs text-sub">
                {fmt(r.rows, 0)} hourly rows · {r.start} → {r.end} · {r.units}.{" "}
                <span className="text-mute">{r.caveat}</span>
              </div>
            )}
          </Q>
        </Panel>

        <Panel title="Exposure summary">
          <Q q={exp} title="Exposure unavailable">
            {(e) => <div className="text-xs text-sub">{e.caveat}</div>}
          </Q>
        </Panel>

        <Panel title="Pipeline warnings">
          <Q q={pipe}>
            {(p) => {
              const bad = Object.entries<any>(p.stages).filter(
                ([, v]) => v.status === "blocked" || v.status === "failed"
              );

              if (!bad.length) {
                return (
                  <div className="text-xs text-gr">
                    No blocked or failed stages.
                  </div>
                );
              }

              return (
                <ul className="max-h-60 space-y-1.5 overflow-y-auto text-xs">
                  {bad.map(([k, v]) => (
                    <li key={k}>
                      <span className="font-mono text-sub">{k}</span>{" "}
                      <Badge s={v.status} />
                      <div className="text-mute">
                        {String(v.message).slice(0, 200)}
                      </div>
                    </li>
                  ))}
                </ul>
              );
            }}
          </Q>
        </Panel>
      </div>
    </div>
  );
}
