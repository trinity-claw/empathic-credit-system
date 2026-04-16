import type {
  AsyncJobResponse,
  CreditRequest,
  CreditResponse,
  EvaluationListResponse,
  EvaluationStats,
  HealthResponse,
  OfferAcceptResponse,
  OfferListResponse,
} from "@/types/api";

/** Browser: same-origin `/api` → Next rewrites to FastAPI (avoids CORS and unreachable docker hostnames like `api`). */
function apiBase(): string {
  if (typeof window !== "undefined") {
    return "/api";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}
const AUTH = btoa(
  `${process.env.NEXT_PUBLIC_API_USER ?? "admin"}:${process.env.NEXT_PUBLIC_API_PASS ?? "changeme"}`
);


function messageFromErrorBody(status: number, raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return `Request failed (${status})`;
  try {
    const j = JSON.parse(trimmed) as { detail?: unknown };
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length > 0) {
      const first = d[0] as { msg?: string };
      if (typeof first?.msg === "string") return first.msg;
    }
  } catch {
  }
  return trimmed.length > 280 ? `${trimmed.slice(0, 277)}…` : trimmed;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Basic ${AUTH}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(messageFromErrorBody(res.status, text));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<HealthResponse>("/health"),

  evaluate: (body: CreditRequest) =>
    apiFetch<CreditResponse>("/credit/evaluate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  evaluateAsync: (body: CreditRequest) =>
    apiFetch<AsyncJobResponse>("/credit/evaluate/async", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // corrected path: /credit/evaluate/{job_id}
  jobStatus: (jobId: string) =>
    apiFetch<AsyncJobResponse>(`/credit/evaluate/${jobId}`),

  acceptOffer: (offerId: string) =>
    apiFetch<OfferAcceptResponse>(`/credit/offers/${offerId}/accept`, {
      method: "POST",
    }),

  evaluations: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit != null) qs.set("limit", String(params.limit));
    if (params?.offset != null) qs.set("offset", String(params.offset));
    return apiFetch<EvaluationListResponse>(`/credit/evaluations?${qs}`);
  },

  evaluationStats: () => apiFetch<EvaluationStats>("/credit/evaluations/stats"),

  offers: (params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.limit != null) qs.set("limit", String(params.limit));
    if (params?.offset != null) qs.set("offset", String(params.offset));
    return apiFetch<OfferListResponse>(`/credit/offers?${qs}`);
  },
};
