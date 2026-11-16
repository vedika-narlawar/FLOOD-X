import { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ApiError } from "../api";

export function Panel({ title, right, children, className = "" }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`border border-line bg-panel ${className}`}>
      {title && (
        <header className="flex items-center justify-between border-b border-line px-3 py-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-sub">{title}</h3>
          {right}
        </header>
      )}
      <div className="p-3">{children}</div>
    </section>
  );
}

const TONE: Record<string, string> = {
  success: "text-gr border-gr/40", ready_for_analysis: "text-gr border-gr/40", ok: "text-gr border-gr/40", available: "text-gr border-gr/40",
  blocked: "text-am border-am/40", blocked_in_environment: "text-am border-am/40", unavailable: "text-am border-am/40", discovered: "text-bl border-bl/40",
  failed: "text-rd border-rd/40", rejected: "text-rd border-rd/40", pending: "text-mute border-line", not_applicable: "text-mute border-line",
  downloaded: "text-cy border-cy/40", parsed: "text-cy border-cy/40", access_verified: "text-cy border-cy/40", quality_checked: "text-cy border-cy/40",
  spatially_validated: "text-cy border-cy/40",
};
export function Badge({ s }: { s: string }) {
  return <span className={`inline-block border px-1.5 py-px font-mono text-[10px] uppercase tracking-wide ${TONE[s] ?? "text-sub border-line"}`}>{s.replace(/_/g, " ")}</span>;
}

export function Unavailable({ error, title }: { error: unknown; title?: string }) {
  const e = error instanceof ApiError ? error : null;
  const d = e?.detail;
  const unreachable = d?.status === "backend_unreachable";
  const upstream = d?.upstream_stages ? Object.entries(d.upstream_stages as Record<string, any>) : [];
  return (
    <div role="alert" className={`border-l-2 ${unreachable ? "border-rd" : "border-am"} bg-raise p-3 text-sm`}>
      <div className={`text-[11px] font-semibold uppercase tracking-widest ${unreachable ? "text-rd" : "text-am"}`}>
        {title ?? (unreachable ? "Backend unreachable" : "Unavailable")}
      </div>
      <p className="mt-1 text-sub">{e?.message ?? "Request failed"}</p>
      {upstream.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-mute">
          {upstream.map(([k, v]) => (
            <li key={k}><span className="font-mono text-sub">{k}</span> <Badge s={v.status} /> <span className="ml-1">{String(v.message).slice(0, 220)}</span></li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Q<T>({ q, children, title }: { q: UseQueryResult<T, ApiError>; children: (d: T) => ReactNode; title?: string }) {
  if (q.isLoading) return <div className="animate-pulse text-xs text-mute" aria-busy="true">Loading…</div>;
  if (q.isError) return <Unavailable error={q.error} title={title} />;
  return <>{children(q.data as T)}</>;
}

export function Stat({ label, value, unit, sub }: { label: string; value: ReactNode; unit?: string; sub?: ReactNode }) {
  return (
    <div className="border border-line bg-panel px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.12em] text-mute">{label}</div>
      <div className="num mt-0.5 font-mono text-xl text-text">{value}{unit && <span className="ml-1 text-xs text-mute">{unit}</span>}</div>
      {sub && <div className="mt-0.5 text-[11px] text-mute">{sub}</div>}
    </div>
  );
}

export const Th = ({ children, right }: { children?: ReactNode; right?: boolean }) => (
  <th className={`border-b border-line px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-mute ${right ? "text-right" : "text-left"}`}>{children}</th>
);
export const Td = ({ children, right, mono }: { children?: ReactNode; right?: boolean; mono?: boolean }) => (
  <td className={`border-b border-line/60 px-2 py-1.5 text-xs ${right ? "text-right" : ""} ${mono ? "num font-mono" : ""}`}>{children}</td>
);

export const fmt = (v: any, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? "—" : typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: d }) : String(v));
