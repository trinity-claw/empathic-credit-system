import type { CreditRequest, CreditResponse, JobStatus } from "@/types/api";

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
  health: () => apiFetch<{ status: string }>("/health"),

  evaluate: (body: CreditRequest) =>
    apiFetch<CreditResponse>("/credit/evaluate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  evaluateAsync: (body: CreditRequest) =>
    apiFetch<{ job_id: string }>("/credit/evaluate/async", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  jobStatus: (jobId: string) =>
    apiFetch<JobStatus>(`/credit/jobs/${jobId}`),

  acceptOffer: (offerId: string) =>
    apiFetch<{ offer_id: string; job_id: string; status: string }>(
      `/credit/offers/${offerId}/accept`,
      { method: "POST" }
    ),
};
