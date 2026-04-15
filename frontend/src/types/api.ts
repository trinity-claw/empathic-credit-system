export interface CreditRequest {
  revolving_utilization: number;
  age: number;
  past_due_30_59: number;
  debt_ratio: number;
  monthly_income: number;
  open_credit_lines: number;
  past_due_90: number;
  real_estate_loans: number;
  past_due_60_89: number;
  dependents: number;
  had_past_due_sentinel: number;
}

export interface ShapExplanation {
  base_value: number;
  shap_values: Record<string, number>;
  top_factors: Array<{ feature: string; impact: number; direction: string }>;
}

export interface CreditResponse {
  request_id: string;
  decision: "APPROVED" | "DENIED";
  score: number;
  probability_of_default: number;
  credit_limit: number;
  interest_rate: number | null;
  credit_type: string | null;
  offer_id: string | null;
  shap_explanation: ShapExplanation;
  model_version: string;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "started" | "finished" | "failed";
  result?: CreditResponse;
}
