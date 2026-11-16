import { Badge, Panel, Q, Stat, Td, Th } from "../components/ui";
import { useApi } from "../api";

export default function Health() {
  const h = useApi<any>("/api/health", { refetchMs: 10000 });
  const s = useApi<any>("/api/status", { refetchMs: 10000 });
  const p = useApi<any>("/api/pipeline/status", { refetchMs: 10000 });
  const ds = useApi<any[]>("/api/datasets", { refetchMs: 30000 });
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Backend" value={h.isError ? "DOWN" : h.data ? "UP" : "…"} sub={h.data?.time} />
        <Q q={s}>{(x) => (<>
          <Stat label="Analytical artifact" value={x.susceptibility_available ? "present" : "absent"} sub={x.active_method} />
          <Stat label="Supervised model" value={x.supervised_model_trained ? "trained" : "none"} sub={`path ${x.active_path}`} />
          <Stat label="Last pipeline activity" value={<span className="text-sm">{x.last_pipeline_activity?.slice(0, 19) ?? "never"}</span>} sub="UTC" />
        </>)}</Q>
      </div>
      <Panel title="Stage state"><Q q={p}>{(d) => (
        <table className="w-full"><thead><tr><Th>Stage</Th><Th>Status</Th><Th>Finished</Th><Th>Message</Th></tr></thead><tbody>
          {d.order.map((n: string) => { const v = d.stages[n]; return <tr key={n}><Td><span className="font-mono">{n}</span></Td><Td><Badge s={v.status} /></Td><Td mono>{v.finished_at?.slice(0, 19) ?? "—"}</Td><Td>{String(v.message).slice(0, 200)}</Td></tr>; })}</tbody></table>)}</Q></Panel>
      
<Panel title="Data-source availability">
  <Q q={ds}>
    {(rows) => (
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((d) => (
          <div
            key={d.id}
            className="border border-line px-3 py-2 text-xs"
          >
            <div className="mb-1 font-mono text-sub">{d.id}</div>
            <div className="mb-2">
              <span className="text-mute">Registry: </span>
              <Badge s={d.status} />
            </div>
            <div>
              <span className="text-mute">Local files: </span>
              {d.local_files_expected > 0 ? (
                <span className={d.local_available ? "text-gr" : "text-am"}>
                  {d.local_files_found}/{d.local_files_expected} found
                </span>
              ) : (
                <span className="text-mute">Not checked</span>
              )}
            </div>
          </div>
        ))}
      </div>
    )}
  </Q>
</Panel>

    </div>
  );
}
