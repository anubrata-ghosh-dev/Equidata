"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import BiasAlert from "@/components/BiasAlert";
import ResultCard from "@/components/ResultCard";
import {
  type FormDataPayload,
  type PredictResponse,
  type ScenarioType,
  toDecisionLabel,
} from "@/services/api";

interface AuditData {
  scenario: ScenarioType;
  input: FormDataPayload;
  output: PredictResponse;
  requestId: string;
  updatedAt: string;
}

const fallbackAuditData: AuditData = {
  scenario: "hiring",
  input: {
    gender: "female",
    caste: "general",
    religion: "hindu",
  },
  output: {
    input_features: {},
    biased_prediction: "Rejected",
    fair_prediction: "Rejected",
    biased_probability: 0,
    fair_probability: 0,
    bias_gap: 0,
    prediction: "Rejected",
    confidence: 0,
    bias_flag: false,
  },
  requestId: "none",
  updatedAt: new Date().toISOString(),
};

export default function AuditPage() {
  const [auditData, setAuditData] = useState<AuditData>(fallbackAuditData);
  const [isFallback, setIsFallback] = useState(true);

  useEffect(() => {
    const raw = window.localStorage.getItem("auditData");
    if (!raw) {
      return;
    }

    try {
      const parsed = JSON.parse(raw) as AuditData;
      setAuditData(parsed);
      setIsFallback(false);
      console.log("AUDIT DATA:", parsed);
    } catch {
      setAuditData(fallbackAuditData);
      setIsFallback(true);
    }
  }, []);

  const hasError = isFallback;
  const errorMessage = isFallback ? "No latest simulation input found. Run the simulator first." : null;

  return (
    <div className="space-y-6">
      <section className="panel p-5 fade-in">
        <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Bias Audit Report</p>
        <h2 className="mt-2 text-2xl font-semibold text-textMain sm:text-3xl">{auditData.scenario.replace("_", " ")} Current Input Audit</h2>
        <p className="mt-2 text-sm text-textMuted">
          {isFallback
            ? "No simulation snapshot found yet. Run a simulation and open this page to audit that same input."
            : `This report displays the exact stored simulator output (ID: ${auditData.requestId}).`}
        </p>
      </section>

      {errorMessage ? <p className="rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{errorMessage}</p> : null}

      {!hasError ? (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ResultCard
              title="Biased Model"
              decision={toDecisionLabel(auditData.output.biased_prediction)}
              confidence={auditData.output.biased_probability * 100}
              subtitle="Decision probability from the model that includes sensitive attributes."
            />
            <ResultCard
              title="Fair Model"
              decision={toDecisionLabel(auditData.output.fair_prediction)}
              confidence={auditData.output.confidence}
              subtitle="Decision probability from the model that excludes sensitive attributes."
            />
          </div>

          {auditData.output.bias_flag ? <BiasAlert /> : null}

          <div className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-3">
            <p className="text-xs uppercase tracking-wide text-textMuted">Gap Summary</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs text-textMuted">Biased Probability</p>
                <p className="text-lg font-semibold text-textMain">{(auditData.output.biased_probability * 100).toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-xs text-textMuted">Fair Probability</p>
                <p className="text-lg font-semibold text-textMain">{(auditData.output.fair_probability * 100).toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-xs text-textMuted">Bias Gap</p>
                <p className="text-lg font-semibold text-accent">{(auditData.output.bias_gap * 100).toFixed(2)}%</p>
              </div>
            </div>
          </div>
        </>
      ) : null}

      <div>
        <Link href="/simulate" className="btn-secondary">
          Back to Simulator
        </Link>
      </div>
    </div>
  );
}
