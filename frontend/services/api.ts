import axios from "axios";

export type DecisionLabel = "Approved" | "Rejected";
export type ScenarioType = "hiring" | "loan_approval" | "college_admission";
export const GENERIC_API_ERROR = "Something went wrong. Try again.";

export interface FormDataPayload {
  gender: string;
  caste: string;
  religion: string;
  experience?: number;
  education_level?: string;
  college_tier?: string;
  skills_score?: number;
  expected_salary?: number;
  loan_amount?: number;
  interest_rate?: number;
  monthly_income?: number;
  profession?: string;
  entrance_score?: number;
  family_income?: number;
  parents_education?: string;
  previous_academic_score?: number;
}

export interface PredictRequest {
  scenario?: ScenarioType;
  features: FormDataPayload;
}

export interface PredictResponse {
  input_features: Record<string, string | number>;
  biased_prediction: "Approved" | "Rejected";
  fair_prediction: "Approved" | "Rejected";
  biased_probability: number;
  fair_probability: number;
  bias_gap: number;
  prediction: "Approved" | "Rejected";
  confidence: number;
  bias_flag: boolean;
}

export interface MitigateRequest extends PredictRequest {}

export interface MitigateResponse extends PredictResponse {}

export interface AuditCurrentRequest {
  scenario: ScenarioType;
  features: FormDataPayload;
}

export interface AuditCurrentResponse {
  input_features: Record<string, string | number>;
  biased_prediction: "Approved" | "Rejected";
  fair_prediction: "Approved" | "Rejected";
  biased_probability: number;
  fair_probability: number;
  bias_gap: number;
  bias_flag: boolean;
  confidence: number;
  contributions: Record<string, number>;
}

export interface BiasDecompositionRequest {
  scenario: ScenarioType;
  features?: FormDataPayload;
}

export interface AttributeBiasBreakdown {
  before_group_rates: Record<string, number>;
  after_group_rates: Record<string, number>;
  before_disparity: number;
  after_disparity: number;
  before_fairness_score: number;
  after_fairness_score: number;
  fairness_improvement: number;
}

export interface CounterfactualAttributeBreakdown {
  biased_bias_score: number;
  fair_model_bias_score: number;
  mitigated_bias_score: number;
  mitigated_probabilities: Record<string, number>;
}

export interface BiasDecompositionResponse {
  dataset_decomposition: Record<string, AttributeBiasBreakdown>;
  counterfactual_decomposition: Record<string, CounterfactualAttributeBreakdown>;
  overall_before_disparity: number;
  overall_after_disparity: number;
}

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

function toApiError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const errorMessage = error.response?.data?.error;
    const detail = error.response?.data?.detail;
    if (typeof errorMessage === "string" && errorMessage.trim().length > 0) {
      return new Error(errorMessage);
    }
    if (typeof detail === "string" && detail.trim().length > 0) {
      return new Error(detail);
    }
  }
  return new Error(GENERIC_API_ERROR);
}

export async function predict(data: PredictRequest): Promise<PredictResponse> {
  try {
    const response = await api.post<PredictResponse>("/predict", {
      scenario: data.scenario ?? "hiring",
      features: data.features,
    });
    return response.data;
  } catch (error: unknown) {
    throw toApiError(error);
  }
}

export async function mitigate(data: MitigateRequest): Promise<MitigateResponse> {
  try {
    const response = await api.post<MitigateResponse>("/mitigate", data);
    return response.data;
  } catch (error: unknown) {
    throw toApiError(error);
  }
}

export async function fetchBiasDecomposition(data: BiasDecompositionRequest): Promise<BiasDecompositionResponse> {
  try {
    const response = await api.post<BiasDecompositionResponse>("/bias/decomposition", data);
    return response.data;
  } catch (error: unknown) {
    throw toApiError(error);
  }
}

export async function fetchCurrentAudit(data: AuditCurrentRequest): Promise<AuditCurrentResponse> {
  try {
    const response = await api.post<AuditCurrentResponse>("/audit/current", data);
    return response.data;
  } catch (error: unknown) {
    throw toApiError(error);
  }
}

export function toDecisionLabel(value: string): DecisionLabel {
  return value === "Approved" ? "Approved" : "Rejected";
}

export default api;
