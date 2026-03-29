"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface ChartsProps {
  maleRate: number;
  femaleRate: number;
  casteRates: Record<string, number>;
  beforeDisparity: number;
  afterDisparity: number;
}

export default function Charts({ maleRate, femaleRate, casteRates, beforeDisparity, afterDisparity }: ChartsProps) {
  const groupData = [
    { group: "Male", selectionRate: Number((maleRate * 100).toFixed(2)) },
    { group: "Female", selectionRate: Number((femaleRate * 100).toFixed(2)) },
  ];

  const casteData = Object.entries(casteRates).map(([group, rate]) => ({
    group: group.toUpperCase(),
    selectionRate: Number((rate * 100).toFixed(2)),
  }));

  const fairnessData = [
    { label: "Before", disparity: Number((beforeDisparity * 100).toFixed(2)) },
    { label: "After", disparity: Number((afterDisparity * 100).toFixed(2)) },
  ];

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <section className="panel p-5 fade-in">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-textMuted">Selection Rate by Group</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={groupData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="group" stroke="#9DA3B6" tickLine={false} axisLine={false} />
              <YAxis stroke="#9DA3B6" tickLine={false} axisLine={false} unit="%" />
              <Tooltip contentStyle={{ background: "#11131a", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 12 }} />
              <Bar dataKey="selectionRate" radius={[8, 8, 0, 0]}>
                {groupData.map((entry) => (
                  <Cell key={entry.group} fill={entry.group === "Male" ? "#5B7CFF" : "#8B5CF6"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel p-5 fade-in">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-textMuted">Before vs After Fairness</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={fairnessData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="label" stroke="#9DA3B6" tickLine={false} axisLine={false} />
              <YAxis stroke="#9DA3B6" tickLine={false} axisLine={false} unit="%" />
              <Tooltip contentStyle={{ background: "#11131a", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 12 }} />
              <Legend />
              <Bar dataKey="disparity" fill="#F43F5E" radius={[8, 8, 0, 0]} name="Disparity (%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel p-5 fade-in">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-textMuted">Selection Rate by Caste</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={casteData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="group" stroke="#9DA3B6" tickLine={false} axisLine={false} />
              <YAxis stroke="#9DA3B6" tickLine={false} axisLine={false} unit="%" />
              <Tooltip contentStyle={{ background: "#11131a", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 12 }} />
              <Bar dataKey="selectionRate" fill="#10B981" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
