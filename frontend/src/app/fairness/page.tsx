"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
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
import { CheckCircle2, AlertTriangle } from "lucide-react";

const AGE_COHORTS = [
  { cohort: "18–30", approval_rate: 0.52, ratio: 0.97 },
  { cohort: "30–45", approval_rate: 0.54, ratio: 1.0 },
  { cohort: "45–60", approval_rate: 0.53, ratio: 0.98 },
  { cohort: "60+", approval_rate: 0.51, ratio: 0.94 },
];

const INCOME_COHORTS = [
  { cohort: "Q4 (alta)", approval_rate: 0.63, ratio: 1.0 },
  { cohort: "Q3", approval_rate: 0.58, ratio: 0.92 },
  { cohort: "Q2", approval_rate: 0.55, ratio: 0.87 },
  { cohort: "Q1 (baixa)", approval_rate: 0.52, ratio: 0.82 },
];

const tooltipStyle = {
  contentStyle: { background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 },
  labelStyle: { color: "#e4e4e7", fontSize: 12 },
};

function CohortChart({ data, title }: { data: typeof AGE_COHORTS; title: string }) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-sm font-medium text-zinc-300">{title}</CardTitle>
        <p className="text-xs text-zinc-500">
          Regra dos 4/5: razão ≥ 0.80 em todos os subgrupos (linha vermelha)
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ left: 0, right: 16 }}>
            <CartesianGrid vertical={false} stroke="#27272a" />
            <XAxis dataKey="cohort" tick={{ fill: "#a1a1aa", fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis domain={[0, 1.1]} tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => v.toFixed(1)} />
            <Tooltip
              {...tooltipStyle}
              formatter={(v, name) => [
                name === "ratio" ? Number(v).toFixed(3) : `${(Number(v) * 100).toFixed(1)}%`,
                name === "ratio" ? "Razão 4/5" : "Taxa de aprovação",
              ]}
            />
            <ReferenceLine y={0.8} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1.5} label={{ value: "0.80", fill: "#ef4444", fontSize: 11, position: "right" }} />
            <Bar dataKey="ratio" radius={[4, 4, 0, 0]}>
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.ratio >= 0.85 ? "#34d399" : entry.ratio >= 0.8 ? "#fbbf24" : "#f87171"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4 space-y-2">
          {data.map((d) => (
            <div key={d.cohort} className="flex items-center justify-between">
              <span className="text-xs text-zinc-400">{d.cohort}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-500">
                  {(d.approval_rate * 100).toFixed(0)}% aprovação
                </span>
                <div className="flex items-center gap-1.5">
                  {d.ratio >= 0.8 ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
                  )}
                  <span className={`text-xs font-medium tabular-nums ${d.ratio >= 0.85 ? "text-emerald-400" : d.ratio >= 0.8 ? "text-yellow-400" : "text-red-400"}`}>
                    {d.ratio.toFixed(3)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function FairnessPage() {
  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Fairness</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Análise de impacto disparatado — Regra dos 4/5 por coortes de idade e renda
        </p>
      </div>

      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wide">Método</p>
              <p className="text-sm text-zinc-200 mt-1">Regra dos 4/5 (EEOC)</p>
              <p className="text-xs text-zinc-500 mt-0.5">
                Taxa de aprovação de qualquer subgrupo deve ser ≥ 80% do grupo com maior taxa.
              </p>
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wide">Resultado por Idade</p>
              <div className="flex items-center gap-2 mt-1">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span className="text-sm text-emerald-400 font-medium">Todos os coortes passam</span>
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">Razão mínima: 0.94 (60+)</p>
            </div>
            <div>
              <p className="text-xs text-zinc-500 uppercase tracking-wide">Resultado por Renda</p>
              <div className="flex items-center gap-2 mt-1">
                <AlertTriangle className="h-4 w-4 text-yellow-400" />
                <span className="text-sm text-yellow-400 font-medium">Q1 no limite</span>
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">Razão Q1: 0.82 — monitorar em produção</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CohortChart data={AGE_COHORTS} title="Fairness por Coorte de Idade" />
        <CohortChart data={INCOME_COHORTS} title="Fairness por Quartil de Renda" />
      </div>

      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-zinc-300">
            Features Emocionais — Análise de Risco Regulatório
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-lg bg-red-900/20 border border-red-800/50 p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-300">Risco LGPD Art. 11</p>
                  <p className="text-xs text-zinc-400 mt-1">
                    Dados emocionais são classificados como dados sensíveis. Exigem consentimento
                    específico, informado e destacado. Finalidade deve ser comprovada.
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-lg bg-emerald-900/20 border border-emerald-800/50 p-4">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-emerald-300">Decisão: Não fazer deploy</p>
                  <p className="text-xs text-zinc-400 mt-1">
                    Delta AUC = -0.0008 (features emocionais pioraram ligeiramente). Custo regulatório
                    supera o benefício preditivo. Experimento documentado e reproduzível.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Separator className="bg-zinc-800" />

          <div className="space-y-2">
            <p className="text-xs text-zinc-500 uppercase tracking-wide">LGPD — Artigos Relevantes</p>
            {[
              { art: "Art. 7", desc: "Bases legais para tratamento. 'Proteção do crédito' cobre dados financeiros, não emocionais." },
              { art: "Art. 11", desc: "Dados sensíveis exigem consentimento específico ou finalidade regulatória explícita." },
              { art: "Art. 18", desc: "Direitos do titular: acesso, correção, portabilidade, eliminação." },
              { art: "Art. 20", desc: "Direito à revisão de decisões automatizadas. SHAP em toda resposta atende esse requisito." },
            ].map((item) => (
              <div key={item.art} className="flex gap-3">
                <Badge variant="outline" className="border-zinc-700 text-zinc-400 shrink-0 text-xs">
                  {item.art}
                </Badge>
                <p className="text-xs text-zinc-400">{item.desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
