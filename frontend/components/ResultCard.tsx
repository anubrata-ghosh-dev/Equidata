interface ResultCardProps {
  title: string;
  decision: "Approved" | "Rejected";
  confidence: number;
  subtitle?: string;
}

export default function ResultCard({ title, decision, confidence, subtitle }: ResultCardProps) {
  const decisionClass = decision === "Approved" ? "text-success" : "text-danger";

  return (
    <section className="panel-soft space-y-3 p-5 fade-in">
      <p className="text-xs uppercase tracking-[0.2em] text-textMuted">{title}</p>
      <div className="flex items-end justify-between gap-3">
        <h3 className={`text-2xl font-semibold ${decisionClass}`}>{decision}</h3>
        <span className="rounded-full border border-white/15 bg-black/25 px-3 py-1 text-xs font-semibold text-textMain">
          Confidence: {confidence.toFixed(1)}%
        </span>
      </div>
      {subtitle ? <p className="text-sm text-textMuted">{subtitle}</p> : null}
    </section>
  );
}
