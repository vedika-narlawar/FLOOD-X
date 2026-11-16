import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ApiError, post, useApi } from "../api";
import { Panel, Td, Th, Unavailable, fmt } from "../components/ui";

export default function Scenario() {
  const cfg = useApi<any>("/api/susceptibility/config");
  const ready = useApi<any>("/api/susceptibility/metadata");
  const [w, setW] = useState<Record<string, number>>({});
  const [rain, setRain] = useState(1);
  const [win, setWin] = useState(24);
  const [name, setName] = useState("scenario-1");
  useEffect(() => { if (cfg.data) setW(Object.fromEntries(cfg.data.variables.map((v: any) => [v.name, v.weight]))); }, [cfg.data]);
  const run = useMutation<any, ApiError, void>({ mutationFn: () => post("/api/scenarios/evaluate", { name, rainfall_multiplier: rain, window_hours: win, weights: w, top_n: 12 }) });
  const res = run.data;
  const hist = res ? res.comparison.score_histogram_bins_0_100.baseline.map((b: number, i: number) => ({ bin: `${i * 10}-${i * 10 + 10}`, baseline: b, scenario: res.comparison.score_histogram_bins_0_100.scenario[i] })) : [];
  const blocked = ready.isError;
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 border-l-2 border-am bg-raise p-3 text-xs text-sub"><b className="text-text">Hypothetical scenario — not a forecast.</b> Scores are relative screening values; they are not observed flood extents, depths or probabilities.</div>
      <Panel title="Configuration" className="col-span-12 lg:col-span-4">
        <label className="block text-[10px] uppercase text-mute">Name</label>
        <input className="mb-3 w-full border border-line bg-ink px-2 py-1 text-xs" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} aria-label="Scenario name" />
        <fieldset className="mb-3 border border-line p-2"><legend className="px-1 text-[10px] uppercase text-mute">Rainfall assumption (recorded, not applied)</legend>
          <label className="text-xs">Multiplier ×{rain.toFixed(2)}</label><input type="range" min={0.5} max={3} step={0.05} value={rain} onChange={(e) => setRain(+e.target.value)} className="w-full" aria-label="Rainfall multiplier" />
          <select className="mt-1 w-full border border-line bg-ink px-1 text-xs" value={win} onChange={(e) => setWin(+e.target.value)} aria-label="Window hours">{[1, 3, 6, 12, 24, 72].map((h) => <option key={h} value={h}>{h} h window</option>)}</select>
          <p className="mt-1 text-[10px] text-mute">The index has no rainfall–runoff relationship, so changing this does not change scores. Shown so the limitation is explicit.</p></fieldset>
        <fieldset className="mb-3 border border-line p-2"><legend className="px-1 text-[10px] uppercase text-mute">Index weights (applied)</legend>
          {cfg.data?.variables.map((v: any) => (<div key={v.name} className="mb-1"><label className="flex justify-between text-xs"><span className="font-mono text-sub">{v.name}</span><span className="num font-mono">{(w[v.name] ?? 0).toFixed(2)}</span></label>
            <input type="range" min={0} max={1} step={0.05} value={w[v.name] ?? 0} onChange={(e) => setW({ ...w, [v.name]: +e.target.value })} className="w-full" aria-label={`Weight ${v.name}`} /></div>))}
          <button className="text-[11px] text-cy underline" onClick={() => setW(Object.fromEntries(cfg.data.variables.map((v: any) => [v.name, v.weight])))}>Reset to baseline weights</button></fieldset>
        <button disabled={blocked || run.isPending} onClick={() => run.mutate()} className="w-full border border-cy bg-cy/10 px-3 py-2 text-xs font-semibold uppercase tracking-widest text-cy disabled:cursor-not-allowed disabled:border-line disabled:text-mute">
          {run.isPending ? "Evaluating…" : "Evaluate scenario"}</button>
        {blocked && <p className="mt-2 text-[11px] text-am">Disabled: {ready.error?.message}</p>}
      </Panel>
      <div className="col-span-12 space-y-4 lg:col-span-8">
        {run.isError && <Unavailable error={run.error} title="Scenario could not be evaluated" />}
        {!res && !run.isError && <Panel><p className="text-xs text-mute">{blocked ? "Scenario evaluation needs the susceptibility index, which has not been computed in this deployment." : "Adjust the weights and evaluate to compare against the baseline."}</p></Panel>}
        {res && (<>
          <Panel title={`Result · id ${res.scenario_id}`}>
            <div className="grid grid-cols-3 gap-3 text-xs"><div>Rank correlation (Spearman)<div className="num font-mono text-lg">{fmt(res.comparison.spearman_rank_correlation, 4)}</div></div>
              <div>Cells changing category<div className="num font-mono text-lg">{res.comparison.cells_changing_category}</div><div className="text-mute">of {res.comparison.n_cells_compared}</div></div>
              <div>Mean score<div className="num font-mono text-lg">{fmt(res.comparison.mean_score.baseline)} → {fmt(res.comparison.mean_score.scenario)}</div></div></div>
          </Panel>
          <Panel title="Score distribution"><div className="h-52"><ResponsiveContainer><BarChart data={hist}><CartesianGrid stroke="#1e2b3b" /><XAxis dataKey="bin" tick={{ fill: "#7d8da1", fontSize: 10 }} /><YAxis tick={{ fill: "#7d8da1", fontSize: 10 }} /><Tooltip contentStyle={{ background: "#0f1722", border: "1px solid #1e2b3b", fontSize: 12 }} /><Legend /><Bar dataKey="baseline" fill="#5b8def" /><Bar dataKey="scenario" fill="#f5a524" /></BarChart></ResponsiveContainer></div></Panel>
          <Panel title="Ward ranking (by mean score)"><table className="w-full"><thead><tr><Th>Ward</Th><Th right>Baseline</Th><Th right>Scenario</Th><Th right>Δ rank</Th></tr></thead><tbody>
            {res.comparison.zone_ranking.map((z: any) => <tr key={z.zone}><Td>{z.zone}</Td><Td right mono>{z.baseline_rank}</Td><Td right mono>{z.scenario_rank}</Td><Td right mono>{z.rank_change > 0 ? `▲${z.rank_change}` : z.rank_change < 0 ? `▼${-z.rank_change}` : "–"}</Td></tr>)}</tbody></table></Panel>
          <Panel title="Assumptions & what was not applied"><ul className="list-disc space-y-1 pl-4 text-xs text-sub">{res.assumptions.map((a: string) => <li key={a}>{a}</li>)}</ul>
            {res.not_applied.map((n: any) => <p key={n.parameter} className="mt-2 border-l-2 border-am pl-2 text-xs text-mute"><b>{n.parameter}:</b> {n.reason}</p>)}</Panel></>)}
      </div>
    </div>
  );
}
