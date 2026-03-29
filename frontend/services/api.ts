import axios from "axios";

export type DecisionLabel = "Approved" | "Rejected";
export const GENERIC_API_ERROR = "Something went wrong. Try again.";

export interface FormDataPayload {
  gender: string;
  race: string;
  religion: string;
  caste: string;
  profession: string;
  income: number;
  education: string;
  experience_years: number;
}

export interface PredictRequest {
  features: FormDataPayload;
  sensitive_column: string;
}

export interface PredictResponse {
  decision: "Approved" | "Rejected";
  confidence: number;
  bias_flag: boolean;
  bias_score: number;
  fairness_score_before: number;
  fairness_score_after: number;
  mitigated_decision: "Approved" | "Rejected";
  mitigated_confidence: number;
  group_metrics: {
    male_rate: number;
    female_rate: number;
    caste_rates: Record<string, number>;
  };
}

export interface MitigateRequest extends PredictRequest {}

export interface MitigateResponse extends PredictResponse {}

export interface BiasDecompositionRequest {
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
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim().length > 0) {
      return new Error(detail);
    }
  }
  return new Error(GENERIC_API_ERROR);
}

export async function predict(data: PredictRequest): Promise<PredictResponse> {
  try {
    const response = await api.post<PredictResponse>("/predict", data);
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

export function toDecisionLabel(value: DecisionLabel): DecisionLabel {
  return value;
}

export default api;
