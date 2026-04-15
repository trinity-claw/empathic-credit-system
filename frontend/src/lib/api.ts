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

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTH = btoa(
  `${process.env.NEXT_PUBLIC_API_USER ?? "admin"}:${process.env.NEXT_PUBLIC_API_PASS ?? "changeme"}`
);

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Basic ${AUTH}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
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
