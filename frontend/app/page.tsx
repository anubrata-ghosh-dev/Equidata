import ScenarioCard from "@/components/ScenarioCard";

const scenarios = [
  {
    title: "Hiring",
    description: "Audit whether candidate screening decisions stay fair across gender groups.",
    icon: "H",
    accentClass: "bg-gradient-to-br from-blue-500 to-indigo-500",
  },
  {
    title: "Loan Approval",
    description: "Stress-test lending outcomes and confidence to catch hidden bias signals quickly.",
    icon: "L",
    accentClass: "bg-gradient-to-br from-violet-500 to-fuchsia-500",
  },
  {
    title: "College Admission",
    description: "Simulate admissions recommendations and compare fairness before and after mitigation.",
    icon: "C",
    accentClass: "bg-gradient-to-br from-cyan-500 to-blue-500",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-7 fade-in">
      <section className="space-y-3">
        <p className="text-xs uppercase tracking-[0.24em] text-textMuted">Scenario Selection</p>
        <h2 className="text-3xl font-semibold text-textMain sm:text-4xl">Choose an AI decision context</h2>
        <p className="max-w-2xl text-sm text-textMuted sm:text-base">
          FairGuard helps you simulate decisions, surface potential bias instantly, and show mitigation impact with
          transparent metrics.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {scenarios.map((scenario) => (
          <ScenarioCard key={scenario.title} {...scenario} />
        ))}
      </section>
    </div>
  );
}
