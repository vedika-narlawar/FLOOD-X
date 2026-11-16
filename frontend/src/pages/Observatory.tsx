
import { useState } from "react";
import { Badge, Panel, Q, Td, Th } from "../components/ui";
import { useApi } from "../api";

export default function Observatory() {
  const ds = useApi<any[]>("/api/datasets");
  const probe = useApi<any>("/api/pipeline/probe");
  const pipe = useApi<any>("/api/pipeline/status");
  const [sel, setSel] = useState<string | null>(null);
  const det = useApi<any>(sel ? `/api/datasets/${sel}` : null);

  return (
    <div className="grid grid-cols-12 gap-4">
      <Panel title="Dataset registry" className="col-span-12">
        <Q q={ds}>
          {(rows) => (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <Th>Dataset</Th>
                    <Th>Registry status</Th>
                    <Th>Local files</Th>
                    <Th>Licence</Th>
                    <Th>Verified</Th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((d) => (
                    <tr
                      key={d.id}
                      className="cursor-pointer hover:bg-raise"
                      onClick={() => setSel(d.id)}
                      tabIndex={0}
                      onKeyDown={(e) =>
                        e.key === "Enter" && setSel(d.id)
                      }
                      aria-label={`Open ${d.name}`}
                    >
                      <Td>
                        <div>{d.name}</div>
                        <div className="font-mono text-[10px] text-mute">
                          {d.id}
                        </div>
                      </Td>
                      <Td>
                        <Badge s={d.status} />
                      </Td>
                      <Td>
                        {d.local_files_expected > 0 ? (
                          <span
                            className={
                              d.local_available
                                ? "text-gr"
                                : "text-am"
                            }
                          >
                            {d.local_files_found}/{d.local_files_expected} found
                          </span>
                        ) : (
                          <span className="text-mute">Not checked</span>
                        )}
                      </Td>
                      <Td>{d.licence}</Td>
                      <Td mono>{d.last_verified?.slice(0, 19) ?? "—"}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Q>
      </Panel>

      <Panel
        title={sel ? "Provenance" : "Select a dataset"}
        className="col-span-12 lg:col-span-5"
      >
        {!sel ? (
          <p className="text-xs text-mute">
            Click a row for provenance, quality checks, processing history and
            blockers.
          </p>
        ) : (
          <Q q={det}>
            {(d) => (
              <div className="space-y-2 text-xs">
                <div>
                  <Badge s={d.status} />{" "}
                  <b className="ml-1">{d.name}</b>
                </div>
                {d.local_files_expected > 0 && (
                  <p>
                    Local files: {d.local_files_found}/
                    {d.local_files_expected} found.{" "}
                    {d.local_available
                      ? "Expected local files are present."
                      : "One or more expected local files are missing."}
                  </p>
                )}
                {d.blocker && (
                  <p className="border-l-2 border-am pl-2 text-am">
                    {d.blocker}
                  </p>
                )}
                <dl className="space-y-0.5 text-sub">
                  <div>
                    <dt className="inline text-mute">Publisher: </dt>
                    {d.publisher}
                  </div>
                  <div>
                    <dt className="inline text-mute">Source: </dt>
                    <span className="break-all">{d.source_url}</span>
                  </div>
                  <div>
                    <dt className="inline text-mute">Attribution: </dt>
                    {d.attribution}
                  </div>
                  <div>
                    <dt className="inline text-mute">Resolution: </dt>
                    {d.spatial_resolution} · {d.temporal_resolution}
                  </div>
                  <div>
                    <dt className="inline text-mute">sha256: </dt>
                    <span className="font-mono">
                      {d.sha256?.slice(0, 20) ?? "—"}
                    </span>
                  </div>
                </dl>
                <div className="text-mute">Known limitations</div>
                <ul className="list-disc pl-4 text-sub">
                  {d.known_limitations.map((l: string) => (
                    <li key={l}>{l}</li>
                  ))}
                </ul>
                <div className="text-mute">Quality checks</div>
                <ul>
                  {d.quality_checks.map((c: any) => (
                    <li key={c.check}>
                      <span className={c.passed ? "text-gr" : "text-rd"}>
                        {c.passed ? "✓" : "✗"}
                      </span>{" "}
                      <span className="font-mono">{c.check}</span>{" "}
                      <span className="text-mute">
                        {String(c.detail).slice(0, 160)}
                      </span>
                    </li>
                  ))}
                  {!d.quality_checks.length && (
                    <li className="text-mute">None executed</li>
                  )}
                </ul>
                <div className="text-mute">Processing history</div>
                <ul className="text-mute">
                  {d.processing_history.map((h: any, i: number) => (
                    <li key={i}>
                      <span className="font-mono">
                        {h.at.slice(0, 19)}
                      </span>{" "}
                      {h.step}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Q>
        )}
      </Panel>

      <Panel
        title="Source access probes (evidence)"
        className="col-span-12 lg:col-span-7"
      >
        <Q q={probe} title="Probe not run">
          {(p) => (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <Th>Dataset</Th>
                    <Th>DNS</Th>
                    <Th>HTTP</Th>
                    <Th>Error</Th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries<any>(p.results).map(([k, v]) => (
                    <tr key={k}>
                      <Td>
                        <span className="font-mono">{k}</span>
                      </Td>
                      <Td>{v.dns_ok ? "OK" : "Fail"}</Td>
                      <Td mono>{v.http_status ?? "—"}</Td>
                      <Td>
                        {String(v.error ?? v.deny_reason ?? "").slice(0, 90)}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Q>
      </Panel>

      <Panel
        title="Pipeline execution history"
        className="col-span-12"
      >
        <Q q={pipe}>
          {(p) => (
            <ul className="max-h-72 space-y-1 overflow-y-auto text-xs">
              {[...p.history].reverse().slice(0, 40).map((h: any, i: number) => (
                <li key={i}>
                  <span className="num font-mono text-mute">
                    {h.finished_at?.slice(0, 19)}
                  </span>{" "}
                  <span className="font-mono text-sub">{h.stage}</span>{" "}
                  <Badge s={h.status} />
                </li>
              ))}
            </ul>
          )}
        </Q>
      </Panel>
    </div>
  );
}
