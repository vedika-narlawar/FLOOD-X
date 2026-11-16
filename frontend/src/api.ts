import { useQuery } from "@tanstack/react-query";

export class ApiError extends Error {
  status: number;
  detail: any;
  constructor(status: number, detail: any) {
    super(typeof detail === "string" ? detail : detail?.reason ?? `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

const BASE = (import.meta as any).env?.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch (e: any) {
    throw new ApiError(0, { status: "backend_unreachable", reason: "Cannot reach the FLOOD-X backend. Start it with `uvicorn backend.app.main:app --port 8000`." });
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? body);
  return body as T;
}

export const get = <T = any>(path: string) => request<T>(path);
export const post = <T = any>(path: string, data: unknown) =>
  request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

export function useApi<T = any>(path: string | null, opts: { refetchMs?: number } = {}) {
  return useQuery<T, ApiError>({
    queryKey: [path],
    queryFn: () => get<T>(path as string),
    enabled: !!path,
    retry: false,
    staleTime: 30_000,
    refetchInterval: opts.refetchMs,
  });
}
