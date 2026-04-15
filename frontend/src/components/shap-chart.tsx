"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface ShapFactor {
  feature: string;
  contribution: number; // matches backend field name
  direction: string;
}

interface ShapChartProps {
  factors: ShapFactor[];
}

const LABEL_MAP: Record<string, string> = {
  revolving_utilization: "Utilização crédito rotativo",
  age: "Idade",
  past_due_30_59: "Atrasos 30-59 dias",
  past_due_60_89: "Atrasos 60-89 dias",
  past_due_90: "Atrasos >90 dias",
  debt_ratio: "Índice de endividamento",
  monthly_income: "Renda mensal",
  open_credit_lines: "Linhas de crédito abertas",
  real_estate_loans: "Empréstimos imobiliários",
  dependents: "Dependentes",
  had_past_due_sentinel: "Flag valor sentinela",
};

export function ShapChart({ factors }: ShapChartProps) {
  const data = [...factors]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .map((f) => ({
      label: LABEL_MAP[f.feature] ?? f.feature,
      impact: f.contribution,
    }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
        <CartesianGrid horizontal={false} stroke="#27272a" />
        <XAxis
          type="number"
          tick={{ fill: "#71717a", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => v.toFixed(2)}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={190}
          tick={{ fill: "#a1a1aa", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#0a120a",
            border: "1px solid rgba(0,230,118,0.2)",
            borderRadius: 8,
            color: "#e8f5e9",
          }}
          labelStyle={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}
          itemStyle={{ color: "#e8f5e9" }}
          formatter={(v) => { const n = Number(v); return [`${n > 0 ? "+" : ""}${n.toFixed(4)}`, "SHAP"]; }}
        />
        <ReferenceLine x={0} stroke="#52525b" />
        <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.impact > 0 ? "#f87171" : "#34d399"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
