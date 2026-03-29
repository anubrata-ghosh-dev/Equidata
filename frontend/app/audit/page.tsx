"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import Charts from "@/components/Charts";
import {
  fetchBiasDecomposition,
  type BiasDecompositionResponse,
  type FormDataPayload,
} from "@/services/api";

interface AuditSnapshot {
  scenario: string;
  maleRate: number;
  femaleRate: number;
  casteRates: Record<string, number>;
  beforeDisparity: number;
  afterDisparity: number;
  fairnessScore: number;
  features?: FormDataPayload;
  updatedAt: string;
}

const fallbackSnapshot: AuditSnapshot = {
  scenario: "Latest Run",
  maleRate: 0,
  femaleRate: 0,
  casteRates: {},
  beforeDisparity: 0,
  afterDisparity: 0,
  fairnessScore: 0,
  features: undefined,
  updatedAt: new Date().toISOString(),
};

export default function AuditPage() {
  const [snapshot, setSnapshot] = useState<AuditSnapshot>(fallbackSnapshot);
  const [isFallback, setIsFallback] = useState(true);
  const [decomposition, setDecomposition] = useState<BiasDecompositionResponse | null>(null);
  const [loadingDecomposition, setLoadingDecomposition] = useState(true);
  const [decompositionError, setDecompositionError] = useState<string | null>(null);

  useEffect(() => {
    const raw = window.sessionStorage.getItem("fairguard_audit");
    if (!raw) {
      return;
    }

    try {
      const parsed = JSON.parse(raw) as AuditSnapshot;
      setSnapshot(parsed);
      setIsFallback(false);
    } catch {
      setSnapshot(fallbackSnapshot);
      setIsFallback(true);
    }
  }, []);

  useEffect(() => {
    const run = async () => {
      setLoadingDecomposition(true);
      setDecompositionError(null);
      try {
        const response = await fetchBiasDecomposition(
          snapshot.features ? { features: snapshot.features } : {},
        );
        setDecomposition(response);
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Failed to load decomposition.";
        setDecompositionError(message);
      } finally {
        setLoadingDecomposition(false);
      }
    };

    void run();
  }, [snapshot.features]);

  const fairnessGain = useMemo(() => {
    return Math.max(0, snapshot.beforeDisparity - snapshot.afterDisparity);
  }, [snapshot.beforeDisparity, snapshot.afterDisparity]);

  const attributeRows = useMemo(() => {
    if (!decomposition) {
      return [];
    }
    return Object.entries(decomposition.dataset_decomposition);
  }, [decomposition]);

  const counterfactualRows = useMemo(() => {
    if (!decomposition) {
      return [];
    }
    return Object.entries(decomposition.counterfactual_decomposition);
  }, [decomposition]);

  return (
    <div className="space-y-6">
      <section className="panel p-5 fade-in">
        <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Bias Audit Report</p>
        <h2 className="mt-2 text-2xl font-semibold text-textMain sm:text-3xl">{snapshot.scenario} Fairness Overview</h2>
        <p className="mt-2 text-sm text-textMuted">
          {isFallback
            ? "No simulation snapshot found yet. Run a simulation and click Fix Bias to populate live audit metrics."
            : "Live metrics from your latest simulation and mitigation run."}
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-wide text-textMuted">Before Disparity</p>
            <p className="mt-1 text-xl font-semibold text-danger">{(snapshot.beforeDisparity * 100).toFixed(1)}%</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-wide text-textMuted">After Disparity</p>
            <p className="mt-1 text-xl font-semibold text-success">{(snapshot.afterDisparity * 100).toFixed(1)}%</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-wide text-textMuted">Fairness Improvement</p>
            <p className="mt-1 text-xl font-semibold text-accent">{(fairnessGain * 100).toFixed(1)}%</p>
          </div>
        </div>
      </section>

      <Charts
        maleRate={snapshot.maleRate}
        femaleRate={snapshot.femaleRate}
        casteRates={snapshot.casteRates}
        beforeDisparity={snapshot.beforeDisparity}
        afterDisparity={snapshot.afterDisparity}
      />

      <section className="panel p-5 fade-in space-y-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Decomposition</p>
          <h3 className="mt-2 text-xl font-semibold text-textMain">Sensitive Attribute Breakdown</h3>
          <p className="mt-2 text-sm text-textMuted">
            Detailed fairness decomposition across gender, caste, and religion from the live backend endpoint.
          </p>
        </div>

        {loadingDecomposition ? <p className="text-sm text-textMuted">Loading decomposition...</p> : null}
        {decompositionError ? (
          <p className="rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{decompositionError}</p>
        ) : null}

        {!loadingDecomposition && !decompositionError ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {attributeRows.map(([attribute, metrics]) => (
              <div key={attribute} className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-2">
                <p className="text-xs uppercase tracking-wide text-textMuted">{attribute}</p>
                <p className="text-sm text-textMuted">
                  Before disparity: <span className="text-danger font-semibold">{(metrics.before_disparity * 100).toFixed(2)}%</span>
                </p>
                <p className="text-sm text-textMuted">
                  After disparity: <span className="text-success font-semibold">{(metrics.after_disparity * 100).toFixed(2)}%</span>
                </p>
                <p className="text-sm text-textMuted">
                  Improvement: <span className="text-accent font-semibold">{(metrics.fairness_improvement * 100).toFixed(2)}%</span>
                </p>
              </div>
            ))}
          </div>
        ) : null}

        {!loadingDecomposition && !decompositionError && decomposition ? (
          <div className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-3">
            <p className="text-xs uppercase tracking-wide text-textMuted">Counterfactual Decomposition</p>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {counterfactualRows.map(([attribute, metrics]) => (
                <div key={attribute} className="space-y-1">
                  <p className="text-sm font-semibold text-textMain">{attribute}</p>
                  <p className="text-xs text-textMuted">Biased score: {metrics.biased_bias_score.toFixed(4)}</p>
                  <p className="text-xs text-textMuted">Fair-model score: {metrics.fair_model_bias_score.toFixed(4)}</p>
                  <p className="text-xs text-textMuted">Mitigated score: {metrics.mitigated_bias_score.toFixed(4)}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      <div>
        <Link href="/simulate" className="btn-secondary">
          Back to Simulator
        </Link>
      </div>
    </div>
  );
}
