import Link from "next/link";

interface ScenarioCardProps {
  title: string;
  description: string;
  icon: string;
  accentClass: string;
}

export default function ScenarioCard({ title, description, icon, accentClass }: ScenarioCardProps) {
  return (
    <Link
      href={`/simulate?scenario=${encodeURIComponent(title)}`}
      className="panel group flex h-full flex-col gap-4 p-5 transition-all duration-300 hover:-translate-y-1 hover:border-white/20 hover:shadow-glow"
    >
      <div
        className={`flex h-12 w-12 items-center justify-center rounded-xl text-xl font-semibold text-white ${accentClass}`}
      >
        {icon}
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-textMain">{title}</h3>
        <p className="text-sm leading-relaxed text-textMuted">{description}</p>
      </div>
      <span className="mt-auto text-sm font-medium text-accent transition-colors duration-200 group-hover:text-white">
        Run Scenario -&gt;
      </span>
    </Link>
  );
}
