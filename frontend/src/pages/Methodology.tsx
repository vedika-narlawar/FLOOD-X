import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Panel, Q, Td, Th, fmt } from "../components/ui";
import { useApi } from "../api";

export default function Methodology() {
  const metrics = useApi<any>("/api/model/metrics");
  const cfg = useApi<any>("/api/susceptibility/config");
  const man = useApi<any>("/api/features/manifest");
  const ex = useApi<any>("/api/model/explainability");
  const meta = useApi<any>("/api/metadata");
  return (
    <div className="grid grid-cols-12 gap-4">
      <Panel title="Active analytical path" className="col-span-12 lg:col-span-6">
        <Q q={metrics}>{(m) => (<div className="space-y-2 text-xs">
          <div><Badge s={m.active_path === "B" ? "ok" : "pending"} /> <b className="ml-2 text-sm">{m.label_audit?.active_method}</b></div>
          <p className="text-sub">{m.reason}</p>
          <p className="border-l-2 border-am pl-2 text-mute">Supervised model trained: <b>{String(m.supervised_model_trained)}</b>. No accuracy, ROC or confusion-matrix figures exist or are shown. Validation status: <b>unvalidated against observed floods</b>.</p>
        </div>)}</Q>
      </Panel>
      <Panel title="Terminology" className="col-span-12 lg:col-span-6">
        <Q q={meta}>{(m) => <dl className="space-y-1 text-xs">{Object.entries<string>(m.terminology).map(([k, v]) => <div key={k}><dt className="inline font-semibold capitalize text-cy">{k}: </dt><dd className="inline text-sub">{v}</dd></div>)}</dl>}</Q>
      </Panel>
      <Panel title="Index formula & weights (inspectable; edit weights in Scenario Studio)" className="col-span-12">
        <Q q={cfg}>{(c) => (<>
          <pre className="mb-3 overflow-x-auto bg-ink p-2 font-mono text-[11px] text-sub">{`score = 100 · Σ_k w_k · n_k / Σ_k w_k      (sum over variables available for the cell; min inputs = ${c.min_inputs})
n_k   = clip((x_k − P${c.normalization.lower_pct}) / (P${c.normalization.upper_pct} − P${c.normalization.lower_pct}), 0, 1); inverted when direction = "decrease"
categories = ${c.categories.method} (${c.categories.labels.length} classes)`}</pre>
          <table className="w-full"><thead><tr><Th>Variable</Th><Th>Direction</Th><Th right>Weight</Th><Th>Rationale</Th></tr></thead><tbody>
            {c.variables.map((v: any) => <tr key={v.name}><Td><span className="font-mono text-sub">{v.name}</span></Td><Td>{v.direction === "increase" ? "↑ higher → more susceptible" : "↓ lower → more susceptible"}</Td><Td right mono>{v.weight.toFixed(2)}</Td><Td>{v.rationale}</Td></tr>)}
            {c.excluded_variables.map((v: any) => <tr key={v.name} className="opacity-70"><Td><span className="font-mono">{v.name}</span></Td><Td><Badge s="unavailable" /></Td><Td right>—</Td><Td>{v.reason}</Td></tr>)}
          </tbody></table>
          <p className="mt-2 text-[11px] text-mute">{c.weights_status}</p></>)}</Q>
      </Panel>
      <Panel title="Feature readiness" className="col-span-12 lg:col-span-7">
        <Q q={man} title="Feature manifest not generated">{(m) => (
          <table className="w-full"><thead><tr><Th>Feature</Th><Th>Status</Th><Th right>Valid cells</Th><Th>Source / reason</Th></tr></thead><tbody>
            {Object.entries<any>(m.features).map(([k, v]) => <tr key={k}><Td><span className="font-mono text-sub">{k}</span></Td><Td><Badge s={v.status} /></Td><Td right mono>{fmt(v.n_valid, 0)}</Td><Td>{v.status === "available" ? v.source_dataset : v.reason}</Td></tr>)}
          </tbody></table>)}</Q>
      </Panel>
      <Panel title="Explainability — mean contribution to score" className="col-span-12 lg:col-span-5">
        <Q q={ex} title="Explainability unavailable">{(e) => (
          <><div className="h-56"><ResponsiveContainer><BarChart layout="vertical" data={Object.entries<number>(e.mean_score_contribution).map(([k, v]) => ({ k, v }))}>
            <CartesianGrid stroke="#1e2b3b" /><XAxis type="number" tick={{ fill: "#7d8da1", fontSize: 10 }} /><YAxis type="category" dataKey="k" width={120} tick={{ fill: "#a9b6c6", fontSize: 10 }} />
            <Tooltip contentStyle={{ background: "#0f1722", border: "1px solid #1e2b3b", fontSize: 12 }} /><Bar dataKey="v" fill="#22d3ee" /></BarChart></ResponsiveContainer></div>
            <p className="text-[11px] text-mute">{e.note}</p></>)}</Q>
      </Panel>
      <Panel title="Weight sensitivity" className="col-span-12">
        <Q q={metrics}>{(m) => m.sensitivity?.computable ? (
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>Mean Spearman vs baseline<div className="num font-mono text-lg">{fmt(m.sensitivity.spearman_vs_baseline.mean, 3)}</div><div className="text-mute">p5 {fmt(m.sensitivity.spearman_vs_baseline.p5, 3)} · {m.sensitivity.n_draws} draws</div></div>
            <div>Top-decile overlap (Jaccard)<div className="num font-mono text-lg">{fmt(m.sensitivity.top_decile_jaccard.mean, 3)}</div><div className="text-mute">min {fmt(m.sensitivity.top_decile_jaccard.min, 3)}</div></div>
            <div className="text-mute">{m.sensitivity.interpretation}</div>
          </div>) : <p className="text-xs text-mute">Sensitivity analysis not available: the index has not been computed (see pipeline status).</p>}</Q>
      </Panel>
    </div>
  );
}
