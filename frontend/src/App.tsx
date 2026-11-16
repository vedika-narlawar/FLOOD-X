import { useEffect, useState } from "react";
import { Badge } from "./components/ui";
import { useApi } from "./api";
import Overview from "./pages/Overview";
import Explorer from "./pages/Explorer";
import Rainfall from "./pages/Rainfall";
import Methodology from "./pages/Methodology";
import Exposure from "./pages/Exposure";
import Scenario from "./pages/Scenario";
import Mitigation from "./pages/Mitigation";
import Observatory from "./pages/Observatory";
import Health from "./pages/Health";


const NAV: [string, string, () => JSX.Element][] = [
  ["overview", "Operations Overview", Overview],
  ["explorer", "Geospatial Explorer", Explorer],
  ["rainfall", "Rainfall Intelligence", Rainfall],
  ["exposure", "Exposure Analysis", Exposure],
  ["data", "Data Observatory", Observatory],
  ["health", "System Health", Health],
];


export default function App() {
  const [page, setPage] = useState(() => location.hash.slice(1) || "overview");
  useEffect(() => { const f = () => setPage(location.hash.slice(1) || "overview"); addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  const Page = (NAV.find((n) => n[0] === page) ?? NAV[0])[2];
  const status = useApi<any>("/api/status", { refetchMs: 20000 });
  return (
    <div className="flex h-full bg-ink text-text">
      <nav aria-label="Primary" className="flex w-52 shrink-0 flex-col border-r border-line bg-panel">
        <div className="border-b border-line px-4 py-3">
          <div className="font-mono text-lg font-bold tracking-tight"><span className="text-cy">FLOOD</span>-X</div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-mute">Pune · Flood Intelligence</div>
        </div>
        <ul className="flex-1 py-2">
          {NAV.map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} aria-current={page === id ? "page" : undefined}
                className={`block border-l-2 px-4 py-2 text-[13px] ${page === id ? "border-cy bg-raise text-text" : "border-transparent text-sub hover:bg-raise/60"}`}>{label}</a>
            </li>
          ))}
        </ul>
        <div className="border-t border-line p-3 text-[11px] text-mute">
          <div className="mb-1 uppercase tracking-widest">Analytical method</div>
          {status.data ? <div className="text-sub">{status.data.active_method ?? "—"}</div> : <div>{status.isError ? "backend offline" : "…"}</div>}
          <div className="mt-2 text-[10px] leading-snug">Relative screening scores. Not flood forecasts or hazard maps.</div>
        </div>
      </nav>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <header className="flex items-center justify-between border-b border-line px-5 py-2.5">
          <h1 className="text-sm font-semibold tracking-wide">{NAV.find((n) => n[0] === page)?.[1] ?? NAV[0][1]}</h1>
          <div className="flex items-center gap-2 text-[11px] text-mute">
            backend <Badge s={status.isError ? "failed" : status.data ? "ok" : "pending"} />
          </div>
        </header>
        <div className="p-5"><Page /></div>
      </main>
    </div>
  );
}
