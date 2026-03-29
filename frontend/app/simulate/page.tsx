"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import BiasAlert from "@/components/BiasAlert";
import ResultCard from "@/components/ResultCard";
import {
  mitigate,
  predict,
  toDecisionLabel,
  type FormDataPayload,
  type MitigateRequest,
  type MitigateResponse,
  type PredictRequest,
  type PredictResponse,
} from "@/services/api";

const DEFAULT_ERROR = "Something went wrong. Try again.";

interface AuditSnapshot {
  scenario: string;
  maleRate: number;
  femaleRate: number;
  casteRates: Record<string, number>;
  beforeDisparity: number;
  afterDisparity: number;
  fairnessScore: number;
  features: FormDataPayload;
  updatedAt: string;
}

const initialFormData: FormDataPayload = {
  gender: "male",
  race: "group_a",
  religion: "hindu",
  caste: "general",
  profession: "tech",
  income: 50000,
  education: "bachelors",
  experience_years: 3,
};

export default function SimulatorPage() {
  const router = useRouter();

  const [formData, setFormData] = useState<FormDataPayload>(initialFormData);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [mitigation, setMitigation] = useState<MitigateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [mitigating, setMitigating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canPredict = useMemo(() => {
    return formData.income >= 0 && formData.experience_years >= 0;
  }, [formData]);

  const predictPayload: PredictRequest = {
    features: formData,
    sensitive_column: "gender",
  };

  const mitigatePayload: MitigateRequest = {
    features: formData,
    sensitive_column: "gender",
  };

  const handleDecision = async () => {
    if (!canPredict || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    setMitigation(null);

    try {
      const response = await predict(predictPayload);
      setPrediction(response);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : DEFAULT_ERROR);
    } finally {
      setLoading(false);
    }
  };

  const handleFixBias = async () => {
    if (!prediction || mitigating) {
      return;
    }

    setMitigating(true);
    setError(null);
    try {
      const response = await mitigate(mitigatePayload);
      setMitigation(response);

      const snapshot: AuditSnapshot = {
        scenario: "Hiring",
        maleRate: response.group_metrics.male_rate,
        femaleRate: response.group_metrics.female_rate,
        casteRates: response.group_metrics.caste_rates,
        beforeDisparity: 1 - response.fairness_score_before,
        afterDisparity: 1 - response.fairness_score_after,
        fairnessScore: response.fairness_score_after,
        features: formData,
        updatedAt: new Date().toISOString(),
      };
      window.sessionStorage.setItem("fairguard_audit", JSON.stringify(snapshot));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : DEFAULT_ERROR);
    } finally {
      setMitigating(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-2 fade-in">
        <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Simulator</p>
        <h2 className="text-2xl font-semibold text-textMain sm:text-3xl">Decision Simulation</h2>
        <p className="text-sm text-textMuted">Provide candidate details, review model output, then mitigate bias in one click.</p>
      </section>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void handleDecision();
        }}
        className="panel space-y-4 p-5 fade-in"
      >
        <h3 className="text-lg font-semibold text-textMain">Decision Inputs</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Gender</span>
            <select
              className="input-field"
              value={formData.gender}
              onChange={(event) => setFormData((prev) => ({ ...prev, gender: event.target.value }))}
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Race</span>
            <select
              className="input-field"
              value={formData.race}
              onChange={(event) => setFormData((prev) => ({ ...prev, race: event.target.value }))}
            >
              <option value="group_a">Group A</option>
              <option value="group_b">Group B</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Religion</span>
            <select
              className="input-field"
              value={formData.religion}
              onChange={(event) => setFormData((prev) => ({ ...prev, religion: event.target.value }))}
            >
              <option value="hindu">Hindu</option>
              <option value="muslim">Muslim</option>
              <option value="christian">Christian</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Caste</span>
            <select
              className="input-field"
              value={formData.caste}
              onChange={(event) => setFormData((prev) => ({ ...prev, caste: event.target.value }))}
            >
              <option value="general">General</option>
              <option value="obc">OBC</option>
              <option value="sc">SC</option>
              <option value="st">ST</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Profession</span>
            <select
              className="input-field"
              value={formData.profession}
              onChange={(event) => setFormData((prev) => ({ ...prev, profession: event.target.value }))}
            >
              <option value="tech">Tech</option>
              <option value="non-tech">Non-Tech</option>
              <option value="business">Business</option>
              <option value="unemployed">Unemployed</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Income</span>
            <input
              className="input-field"
              type="number"
              min={0}
              value={formData.income}
              onChange={(event) => setFormData((prev) => ({ ...prev, income: Number(event.target.value) }))}
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Education</span>
            <select
              className="input-field"
              value={formData.education}
              onChange={(event) => setFormData((prev) => ({ ...prev, education: event.target.value }))}
            >
              <option value="bachelors">Bachelors</option>
              <option value="masters">Masters</option>
              <option value="phd">PhD</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Experience</span>
            <input
              className="input-field"
              type="number"
              min={0}
              value={formData.experience_years}
              onChange={(event) => setFormData((prev) => ({ ...prev, experience_years: Number(event.target.value) }))}
            />
          </label>
        </div>

        <button
          type="submit"
          className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading || !canPredict}
        >
          {loading ? "Processing..." : "Get Decision"}
        </button>
      </form>

      {error ? <p className="rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{error}</p> : null}

      {prediction ? (
        <div className="space-y-4">
          <ResultCard
            title="Initial Decision"
            decision={toDecisionLabel(prediction.decision)}
            confidence={prediction.confidence}
            subtitle={`Generated by baseline model. Bias flag: ${prediction.bias_flag ? "true" : "false"}. Bias score: ${prediction.bias_score.toFixed(3)}.`}
          />

          {prediction.bias_flag ? <BiasAlert /> : null}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="btn-primary"
              onClick={handleFixBias}
              disabled={mitigating}
            >
              {mitigating ? "Processing..." : "Fix Bias"}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => router.push("/audit")}
            >
              Open Audit Report
            </button>
          </div>
        </div>
      ) : null}

      {mitigation ? (
        <ResultCard
          title="Mitigated Decision"
          decision={toDecisionLabel(mitigation.mitigated_decision)}
          confidence={mitigation.mitigated_confidence}
          subtitle={`Fairness before: ${(mitigation.fairness_score_before * 100).toFixed(1)}%, after: ${(mitigation.fairness_score_after * 100).toFixed(1)}%.`}
        />
      ) : null}
    </div>
  );
}
