"use client";

import { type FormEvent, useMemo, useState } from "react";

export interface DecisionFormValues {
  gender: string;
  income: number;
  education: string;
  experience: number;
}

interface InputFormProps {
  loading?: boolean;
  onSubmit: (values: DecisionFormValues) => Promise<void>;
}

const defaultValues: DecisionFormValues = {
  gender: "female",
  income: 55000,
  education: "bachelors",
  experience: 3,
};

export default function InputForm({ loading = false, onSubmit }: InputFormProps) {
  const [values, setValues] = useState<DecisionFormValues>(defaultValues);

  const canSubmit = useMemo(() => {
    return values.income >= 0 && values.experience >= 0;
  }, [values]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || loading) {
      return;
    }
    await onSubmit(values);
  };

  return (
    <form onSubmit={handleSubmit} className="panel space-y-4 p-5 fade-in">
      <h2 className="text-lg font-semibold text-textMain">Decision Inputs</h2>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="space-y-2">
          <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Gender</span>
          <select
            className="input-field"
            value={values.gender}
            onChange={(event) => setValues((prev) => ({ ...prev, gender: event.target.value }))}
          >
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
        </label>

        <label className="space-y-2">
          <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Income</span>
          <input
            className="input-field"
            type="number"
            min={0}
            value={values.income}
            onChange={(event) => setValues((prev) => ({ ...prev, income: Number(event.target.value) }))}
          />
        </label>

        <label className="space-y-2">
          <span className="text-xs font-medium uppercase tracking-wider text-textMuted">Education</span>
          <select
            className="input-field"
            value={values.education}
            onChange={(event) => setValues((prev) => ({ ...prev, education: event.target.value }))}
          >
            <option value="high_school">High School</option>
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
            value={values.experience}
            onChange={(event) => setValues((prev) => ({ ...prev, experience: Number(event.target.value) }))}
          />
        </label>
      </div>

      <button type="submit" disabled={!canSubmit || loading} className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60">
        {loading ? "Evaluating..." : "Get Decision"}
      </button>
    </form>
  );
}
