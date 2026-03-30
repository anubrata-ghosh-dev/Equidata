"use client";

import { useEffect, useMemo, useState } from "react";
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
  type ScenarioType,
} from "@/services/api";

const DEFAULT_ERROR = "Something went wrong. Try again.";

interface AuditSnapshot {
  scenario: ScenarioType;
  input: FormDataPayload;
  output: PredictResponse;
  requestId: string;
  updatedAt: string;
}

function normalizeScenario(value: string | null): ScenarioType {
  const raw = (value ?? "hiring").toLowerCase().replace(/\s+/g, "_");
  if (raw === "loan" || raw === "loanapproval") return "loan_approval";
  if (raw === "college" || raw === "collegeadmission") return "college_admission";
  if (raw === "loan_approval" || raw === "college_admission" || raw === "hiring") return raw;
  return "hiring";
}

function initialFormForScenario(scenario: ScenarioType): FormDataPayload {
  if (scenario === "loan_approval") {
    return {
      loan_amount: 800000,
      interest_rate: 10.5,
      monthly_income: 70000,
      profession: "salaried",
      gender: "female",
      caste: "general",
      religion: "hindu",
    };
  }

  if (scenario === "college_admission") {
    return {
      entrance_score: 78,
      family_income: 550000,
      parents_education: "graduate",
      previous_academic_score: 82,
      gender: "female",
      caste: "general",
      religion: "hindu",
    };
  }

  return {
    experience: 4,
    education_level: "bachelors",
    college_tier: "other",
    skills_score: 72,
    expected_salary: 90000,
    gender: "female",
    caste: "general",
    religion: "hindu",
  };
}

export default function SimulatorPage() {
  const router = useRouter();

  const [scenario, setScenario] = useState<ScenarioType>("hiring");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const parsedScenario = normalizeScenario(params.get("scenario"));
    setScenario(parsedScenario);
    setFormData(initialFormForScenario(parsedScenario));
  }, []);

  const [formData, setFormData] = useState<FormDataPayload>(() => initialFormForScenario(scenario));
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [mitigation, setMitigation] = useState<MitigateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [mitigating, setMitigating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canPredict = useMemo(() => {
    if (scenario === "hiring") {
      return (
        (formData.experience ?? 0) >= 0 &&
        (formData.skills_score ?? 0) >= 0 &&
        (formData.expected_salary ?? 0) >= 0
      );
    }
    if (scenario === "loan_approval") {
      return (
        (formData.loan_amount ?? 0) > 0 &&
        (formData.interest_rate ?? 0) > 0 &&
        (formData.monthly_income ?? 0) > 0
      );
    }
    return (
      (formData.entrance_score ?? 0) >= 0 &&
      (formData.family_income ?? 0) >= 0 &&
      (formData.previous_academic_score ?? 0) >= 0
    );
  }, [formData, scenario]);

  const predictPayload: PredictRequest = { scenario, features: formData };

  const mitigatePayload: MitigateRequest = { scenario, features: formData };

  const handleDecision = async () => {
    if (!canPredict || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    setMitigation(null);

    try {
      console.log("[Simulator] Starting prediction with payload:", predictPayload);
      const response = await predict(predictPayload);
      console.log("SIMULATOR RESULT:", response);
      setPrediction(response);

      // Persist exact input/output snapshot for display-only audit view.
      const requestId = `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      const snapshot: AuditSnapshot = {
        scenario,
        input: formData,
        output: response,
        requestId,
        updatedAt: new Date().toISOString(),
      };

      window.localStorage.setItem("auditData", JSON.stringify(snapshot));
      console.log(`[Simulator] Stored auditData snapshot (requestId: ${requestId})`);
    } catch (err: unknown) {
      console.error("[Simulator] Prediction failed:", err);
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : DEFAULT_ERROR);
    } finally {
      setMitigating(false);
    }
  };

  const scenarioTitle =
    scenario === "hiring" ? "Hiring" : scenario === "loan_approval" ? "Loan Approval" : "College Admission";

  return (
    <div className="space-y-6">
      <section className="space-y-2 fade-in">
        <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Simulator</p>
        <h2 className="text-2xl font-semibold text-textMain sm:text-3xl">{scenarioTitle} Decision Simulation</h2>
        <p className="text-sm text-textMuted">Domain-specific inputs feed two models: biased baseline vs fair model.</p>
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
          {scenario === "hiring" ? (
            <>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Experience (Years)</span>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  value={formData.experience ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, experience: Number(event.target.value) }))}
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Education Level</span>
                <select
                  className="input-field"
                  value={formData.education_level ?? "bachelors"}
                  onChange={(event) => setFormData((prev) => ({ ...prev, education_level: event.target.value }))}
                >
                  <option value="high_school">High School</option>
                  <option value="bachelors">Bachelors</option>
                  <option value="masters">Masters</option>
                  <option value="phd">PhD</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">College Tier</span>
                <select
                  className="input-field"
                  value={formData.college_tier ?? "Other"}
                  onChange={(event) => setFormData((prev) => ({ ...prev, college_tier: event.target.value }))}
                >
                  <option value="IIT">IIT</option>
                  <option value="NIT">NIT</option>
                  <option value="Other">Other</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Skills Score (0-100)</span>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  max={100}
                  value={formData.skills_score ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, skills_score: Number(event.target.value) }))}
                />
              </label>

              <label className="space-y-2 sm:col-span-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Expected Salary</span>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  value={formData.expected_salary ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, expected_salary: Number(event.target.value) }))}
                />
              </label>
            </>
          ) : null}

          {scenario === "loan_approval" ? (
            <>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Loan Amount</span>
                <input
                  className="input-field"
                  type="number"
                  min={1000}
                  value={formData.loan_amount ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, loan_amount: Number(event.target.value) }))}
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Interest Rate (%)</span>
                <input
                  className="input-field"
                  type="number"
                  min={1}
                  step={0.1}
                  value={formData.interest_rate ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, interest_rate: Number(event.target.value) }))}
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Monthly Income</span>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  value={formData.monthly_income ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, monthly_income: Number(event.target.value) }))}
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Profession</span>
                <select
                  className="input-field"
                  value={formData.profession ?? "salaried"}
                  onChange={(event) => setFormData((prev) => ({ ...prev, profession: event.target.value }))}
                >
                  <option value="salaried">Salaried</option>
                  <option value="self_employed">Self Employed</option>
                  <option value="business">Business</option>
                  <option value="student">Student</option>
                </select>
              </label>
            </>
          ) : null}

          {scenario === "college_admission" ? (
            <>
              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Entrance Score</span>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  max={100}
                  value={formData.entrance_score ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, entrance_score: Number(event.target.value) }))}
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Family Income</span>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  value={formData.family_income ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, family_income: Number(event.target.value) }))}
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Parents Education</span>
                <select
                  className="input-field"
                  value={formData.parents_education ?? "school"}
                  onChange={(event) => setFormData((prev) => ({ ...prev, parents_education: event.target.value }))}
                >
                  <option value="none">None</option>
                  <option value="school">School</option>
                  <option value="graduate">Graduate</option>
                  <option value="postgraduate">Postgraduate</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Previous Academic Score</span>
                <input
                  className="input-field"
                  type="number"
                  min={0}
                  max={100}
                  value={formData.previous_academic_score ?? 0}
                  onChange={(event) => setFormData((prev) => ({ ...prev, previous_academic_score: Number(event.target.value) }))}
                />
              </label>
            </>
          ) : null}

          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Gender (Audit Only)</span>
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
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Caste (Audit Only)</span>
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

          <label className="space-y-2 sm:col-span-2">
            <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Religion (Audit Only)</span>
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
            title="Fair Model Decision"
            decision={toDecisionLabel(prediction.prediction)}
            confidence={prediction.confidence}
            subtitle={`Prediction returned by the fair model using non-sensitive decision features.`}
          />

          {prediction.bias_flag ? <BiasAlert /> : null}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="btn-primary"
              onClick={handleFixBias}
              disabled={mitigating}
            >
              {mitigating ? "Processing..." : "Run Fair Check"}
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
          title="Fairness Re-check"
          decision={toDecisionLabel(mitigation.prediction)}
          confidence={mitigation.confidence}
          subtitle={`Re-evaluated output after mitigation flow.`}
        />
      ) : null}
    </div>
  );
}
