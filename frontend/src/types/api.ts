export interface CreditRequest {
  revolving_utilization: number;
  age: number;
  past_due_30_59: number;
  debt_ratio: number;
  monthly_income: number | null;
  open_credit_lines: number;
  past_due_90: number;
  real_estate_loans: number;
  past_due_60_89: number;
  dependents: number | null;
  had_past_due_sentinel: number;
  // optional emotional fields
  stress_level?: number | null;
  impulsivity_score?: number | null;
  emotional_stability?: number | null;
  financial_stress_events_7d?: number | null;
}

export interface ShapFactor {
  feature: string;
  contribution: number; // backend field name
  direction: string;    // "increases_risk" | "decreases_risk"
}

export interface ShapExplanation {
  base_value: number;
  prediction: number;
  contributions: Record<string, number>; // backend field name
}

export interface CreditResponse {
  request_id: string;
  decision: "APPROVED" | "DENIED";
  probability_of_default: number;
  score: number;
  credit_limit: number;
  interest_rate: number | null;
  credit_type: string | null;
  offer_id: string | null;
  model_used: string;
  shap_explanation: ShapExplanation;
  top_factors: ShapFactor[];
}

export interface AsyncJobResponse {
  job_id: string;
  status: "queued" | "started" | "finished" | "failed";
  result?: CreditResponse;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  model_version: string;
}

export interface OfferAcceptResponse {
  offer_id: string;
  job_id: string;
  status: string;
}

export interface EvaluationSummary {
  request_id: string;
  decision: string;
  score: number;
  probability_of_default: number;
  model_used: string;
  created_at: string;
  request_payload: Record<string, unknown>;
  shap_explanation: ShapExplanation;
}

export interface EvaluationListResponse {
  items: EvaluationSummary[];
  total: number;
}

export interface EvaluationStats {
  total_evaluations: number;
  approval_rate: number;
  avg_score: number;
  pending_offers: number;
  tier_distribution: Record<string, number>;
}

export interface OfferSummary {
  offer_id: string;
  evaluation_id: string;
  credit_limit: number;
  interest_rate: number;
  credit_type: string;
  status: string;
  created_at: string;
}

export interface OfferListResponse {
  items: OfferSummary[];
  total: number;
}
