"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import type { EvaluationStats } from "@/types/api";

const SCORE_DISTRIBUTION = [
  { range: "0–100", bons: 12, maus: 88 },
  { range: "100–200", bons: 28, maus: 72 },
  { range: "200–300", bons: 41, maus: 59 },
  { range: "300–400", bons: 62, maus: 38 },
  { range: "400–500", bons: 78, maus: 22 },
  { range: "500–600", bons: 88, maus: 12 },
  { range: "600–700", bons: 94, maus: 6 },
  { range: "700–800", bons: 98, maus: 2 },
  { range: "800–900", bons: 99.2, maus: 0.8 },
  { range: "900–1000", bons: 99.8, maus: 0.2 },
];

const ROC_CURVE = [
  { fpr: 0, tpr: 0 },
  { fpr: 0.02, tpr: 0.18 },
  { fpr: 0.05, tpr: 0.35 },
  { fpr: 0.1, tpr: 0.52 },
  { fpr: 0.15, tpr: 0.63 },
  { fpr: 0.2, tpr: 0.71 },
  { fpr: 0.3, tpr: 0.82 },
  { fpr: 0.4, tpr: 0.89 },
  { fpr: 0.5, tpr: 0.93 },
  { fpr: 0.6, tpr: 0.96 },
  { fpr: 0.8, tpr: 0.98 },
  { fpr: 1, tpr: 1 },
];

const CALIBRATION_DATA = [
  { predicted: 0.02, actual: 0.019 },
  { predicted: 0.05, actual: 0.048 },
  { predicted: 0.08, actual: 0.079 },
  { predicted: 0.12, actual: 0.118 },
  { predicted: 0.18, actual: 0.175 },
  { predicted: 0.25, actual: 0.248 },
  { predicted: 0.35, actual: 0.352 },
  { predicted: 0.50, actual: 0.496 },
  { predicted: 0.65, actual: 0.651 },
  { predicted: 0.80, actual: 0.803 },
];

const MODEL_COMPARISON = [
  { model: "LogReg", auc: 0.8216, ks: 0.5012, brier: 0.1545 },
  { model: "XGB Bruto", auc: 0.8676, ks: 0.5764, brier: 0.0550 },
  { model: "XGB Calib.", auc: 0.8676, ks: 0.5764, brier: 0.0488 },
  { model: "XGB + Emo.", auc: 0.8668, ks: 0.5751, brier: 0.0492 },
];

const tooltipStyle = {
  contentStyle: { background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 },
  labelStyle: { color: "#e4e4e7", fontSize: 12 },
};

const TIER_COLORS: Record<string, string> = {
  "850+": "#34d399",
  "700-849": "#60a5fa",
  "550-699": "#fbbf24",
  "<550": "#f87171",
};

export default function AnalyticsPage() {
  const [stats, setStats] = useState<EvaluationStats | null>(null);

  useEffect(() => {
    api.evaluationStats().then(setStats).catch(() => null);
  }, []);

  const tierData = stats
    ? Object.entries(stats.tier_distribution).map(([range, count]) => ({ range, count }))
    : [];

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Analytics</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Performance do modelo · Give Me Some Credit (n=150.000) + dados operacionais em tempo real
        </p>
      </div>

      <Tabs defaultValue="operacional">
        <TabsList className="bg-zinc-800 border border-zinc-700">
          <TabsTrigger value="operacional" className="data-[state=active]:bg-zinc-700 text-zinc-400 data-[state=active]:text-zinc-100">
            Operacional
          </TabsTrigger>
          <TabsTrigger value="distribution" className="data-[state=active]:bg-zinc-700 text-zinc-400 data-[state=active]:text-zinc-100">
            Distribuição
          </TabsTrigger>
          <TabsTrigger value="roc" className="data-[state=active]:bg-zinc-700 text-zinc-400 data-[state=active]:text-zinc-100">
            Curva ROC
          </TabsTrigger>
          <TabsTrigger value="calibration" className="data-[state=active]:bg-zinc-700 text-zinc-400 data-[state=active]:text-zinc-100">
            Calibração
          </TabsTrigger>
          <TabsTrigger value="comparison" className="data-[state=active]:bg-zinc-700 text-zinc-400 data-[state=active]:text-zinc-100">
            Modelos
          </TabsTrigger>
        </TabsList>

        {/* Operational tab — real data from the running API */}
        <TabsContent value="operacional" className="mt-4">
          {stats === null ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Skeleton className="h-64 w-full bg-zinc-800 rounded-xl" />
              <Skeleton className="h-64 w-full bg-zinc-800 rounded-xl" />
            </div>
          ) : stats.total_evaluations === 0 ? (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="flex flex-col items-center gap-2 py-16 text-zinc-600">
                <p className="text-sm">Nenhuma avaliação processada ainda.</p>
                <p className="text-xs">
                  Os dados operacionais aparecem conforme o sistema for usado.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <Card className="bg-zinc-900 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-zinc-300">
                    Distribuição por Tier — Avaliações Reais
                  </CardTitle>
                  <p className="text-xs text-zinc-500">
                    {stats.total_evaluations.toLocaleString("pt-BR")} avaliações ·{" "}
                    {(stats.approval_rate * 100).toFixed(1)}% aprovadas
                  </p>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={tierData} margin={{ left: 0, right: 8 }}>
                      <CartesianGrid vertical={false} stroke="#27272a" />
                      <XAxis
                        dataKey="range"
                        tick={{ fill: "#a1a1aa", fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#71717a", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip
                        {...tooltipStyle}
                        formatter={(v) => [v, "Avaliações"]}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {tierData.map((entry) => (
                          <Cell
                            key={entry.range}
                            fill={TIER_COLORS[entry.range] ?? "#6366f1"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-zinc-300">
                    KPIs Operacionais
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      {
                        label: "Total avaliações",
                        value: stats.total_evaluations.toLocaleString("pt-BR"),
                      },
                      {
                        label: "Taxa aprovação",
                        value: `${(stats.approval_rate * 100).toFixed(1)}%`,
                      },
                      {
                        label: "Score médio",
                        value: stats.avg_score.toFixed(0),
                      },
                      {
                        label: "Ofertas pendentes",
                        value: stats.pending_offers.toLocaleString("pt-BR"),
                      },
                    ].map((kpi) => (
                      <div key={kpi.label} className="rounded-lg bg-zinc-800/50 p-3">
                        <p className="text-xs text-zinc-500">{kpi.label}</p>
                        <p className="text-xl font-bold text-zinc-100 mt-1 tabular-nums">
                          {kpi.value}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="distribution" className="mt-4">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-zinc-300">
                Distribuição por Faixa de Score — % Bons vs Maus
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={SCORE_DISTRIBUTION} margin={{ left: 0, right: 16 }}>
                  <CartesianGrid vertical={false} stroke="#27272a" />
                  <XAxis dataKey="range" tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false} unit="%" />
                  <Tooltip {...tooltipStyle} formatter={(v, name) => [`${v}%`, name === "bons" ? "Bons pagadores" : "Maus pagadores"]} />
                  <Bar dataKey="bons" stackId="a" fill="#34d399" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="maus" stackId="a" fill="#f87171" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-xs text-zinc-500 mt-3 text-center">
                Quanto mais alto o score, maior a concentração de bons pagadores — separação nítida a partir do score 600.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roc" className="mt-4">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-zinc-300">
                Curva ROC — AUC = 0.8676
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={ROC_CURVE} margin={{ left: 0, right: 16 }}>
                  <defs>
                    <linearGradient id="aucGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#27272a" />
                  <XAxis dataKey="fpr" tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} label={{ value: "FPR", position: "insideBottomRight", offset: -4, fill: "#71717a", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} label={{ value: "TPR", angle: -90, position: "insideLeft", fill: "#71717a", fontSize: 11 }} />
                  <Tooltip {...tooltipStyle} formatter={(v) => [`${(Number(v) * 100).toFixed(1)}%`]} />
                  <Area type="monotone" dataKey="tpr" stroke="#6366f1" strokeWidth={2.5} fill="url(#aucGrad)" />
                </AreaChart>
              </ResponsiveContainer>
              <p className="text-xs text-zinc-500 mt-3 text-center">
                AUC 0.87 — para qualquer par aleatório bom/mau, o modelo acerta o ranking em 87% dos casos.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="calibration" className="mt-4">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-zinc-300">
                Curva de Calibração — Brier Score = 0.0488
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={CALIBRATION_DATA} margin={{ left: 0, right: 16 }}>
                  <CartesianGrid stroke="#27272a" />
                  <XAxis dataKey="predicted" tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} label={{ value: "Prob. Prevista", position: "insideBottomRight", offset: -4, fill: "#71717a", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} label={{ value: "Freq. Real", angle: -90, position: "insideLeft", fill: "#71717a", fontSize: 11 }} />
                  <Tooltip {...tooltipStyle} formatter={(v) => [`${(Number(v) * 100).toFixed(1)}%`]} />
                  <Line type="monotone" dataKey="predicted" stroke="#52525b" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="Perfeito" />
                  <Line type="monotone" dataKey="actual" stroke="#34d399" strokeWidth={2.5} dot={{ fill: "#34d399", r: 4 }} name="Modelo" />
                </LineChart>
              </ResponsiveContainer>
              <p className="text-xs text-zinc-500 mt-3 text-center">
                Calibração isotônica corrigiu o Brier de 0.055 → 0.049. Linha verde próxima da diagonal perfeita (cinza).
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="comparison" className="mt-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {[
              { key: "auc", label: "AUC-ROC", better: "maior", format: (v: number) => v.toFixed(4) },
              { key: "ks", label: "KS Statistic", better: "maior", format: (v: number) => v.toFixed(4) },
              { key: "brier", label: "Brier Score", better: "menor", format: (v: number) => v.toFixed(4) },
            ].map(({ key, label, better, format }) => (
              <Card key={key} className="bg-zinc-900 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-zinc-300">
                    {label}
                    <span className="text-xs text-zinc-600 font-normal ml-2">({better} é melhor)</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={MODEL_COMPARISON} layout="vertical" margin={{ left: 8, right: 16 }}>
                      <CartesianGrid horizontal={false} stroke="#27272a" />
                      <XAxis type="number" domain={[key === "brier" ? 0 : 0.75, key === "brier" ? 0.2 : 1]} tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} axisLine={false} />
                      <YAxis type="category" dataKey="model" width={80} tick={{ fill: "#a1a1aa", fontSize: 12 }} tickLine={false} axisLine={false} />
                      <Tooltip {...tooltipStyle} formatter={(v) => [format(Number(v))]} />
                      <Bar dataKey={key} radius={[0, 4, 4, 0]}>
                        {MODEL_COMPARISON.map((entry, i) => (
                          <Cell
                            key={i}
                            fill={entry.model === "XGB Calib." ? "#6366f1" : "#3f3f46"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            ))}
          </div>
          <p className="text-xs text-zinc-600 text-center mt-3">
            XGB + Emocional (roxo claro) vs XGB Calibrado (indigo) — features emocionais não agregam valor preditivo.
          </p>
        </TabsContent>
      </Tabs>
    </div>
  );
}
