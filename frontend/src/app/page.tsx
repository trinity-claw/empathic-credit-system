"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { MetricCard } from "@/components/metric-card";
import { api } from "@/lib/api";
import type { EvaluationStats, EvaluationSummary } from "@/types/api";
import { CheckCircle2, XCircle, ArrowRight, InboxIcon } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const DESIGN_DECISIONS = [
  {
    choice: "XGBoost + Isotonic Calibration",
    rationale: "AUC 0.87 vs 0.82 baseline. Calibração reduz Brier de 0.055 → 0.049.",
  },
  {
    choice: "SHAP TreeExplainer (exato)",
    rationale:
      "Valores de Shapley exatos em O(TLD). Legalmente defensável para Art. 20 LGPD.",
  },
  {
    choice: "Features emocionais: não deployadas",
    rationale: "Delta AUC = -0.0008. Custo regulatório (LGPD Art. 11) supera o benefício.",
  },
  {
    choice: "SQLite + rq",
    rationale: "Zero ops. ACID. Migração para Postgres é uma variável de config.",
  },
];

const TIER_COLORS: Record<string, string> = {
  "850+": "#34d399",
  "700-849": "#60a5fa",
  "550-699": "#fbbf24",
  "<550": "#f87171",
};

function StatsSkeletons() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i} className="bg-transparent border-0">
          <CardHeader className="pb-2">
            <Skeleton className="h-3 w-24 bg-zinc-800" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-7 w-16 bg-zinc-800" />
            <Skeleton className="h-3 w-32 bg-zinc-800 mt-2" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function RecentSkeletons() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="h-4 w-4 rounded-full bg-zinc-800" />
            <div>
              <Skeleton className="h-4 w-24 bg-zinc-800" />
              <Skeleton className="h-3 w-16 bg-zinc-800 mt-1" />
            </div>
          </div>
          <Skeleton className="h-6 w-20 bg-zinc-800" />
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<EvaluationStats | null>(null);
  const [recent, setRecent] = useState<EvaluationSummary[] | null>(null);
  const [statsError, setStatsError] = useState(false);

  useEffect(() => {
    api
      .evaluationStats()
      .then(setStats)
      .catch(() => setStatsError(true));
    api
      .evaluations({ limit: 8 })
      .then((r) => setRecent(r.items))
      .catch(() => setRecent([]));
  }, []);

  const tierData = stats
    ? Object.entries(stats.tier_distribution).map(([range, count]) => ({
        range,
        count,
      }))
    : [];

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Empathic Credit System — XGBoost · SHAP · FastAPI
        </p>
      </div>

      {/* KPI cards */}
      {stats === null && !statsError ? (
        <StatsSkeletons />
      ) : statsError ? (
        <div className="rounded-lg border border-dashed border-zinc-800 p-6 text-center text-sm text-zinc-600">
          Não foi possível carregar as métricas. Verifique se a API está rodando.
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            title="Total de Avaliações"
            value={stats!.total_evaluations.toLocaleString("pt-BR")}
            subtitle="Avaliações processadas"
          />
          <MetricCard
            title="Taxa de Aprovação"
            value={`${(stats!.approval_rate * 100).toFixed(1)}%`}
            subtitle="Decisões APROVADO"
            trend="up"
          />
          <MetricCard
            title="Score Médio"
            value={stats!.avg_score.toFixed(0)}
            subtitle="Escala 0–1000"
          />
          <MetricCard
            title="Ofertas Pendentes"
            value={stats!.pending_offers.toLocaleString("pt-BR")}
            subtitle="Aguardando aceitação"
          />
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent evaluations */}
        <Card className="bg-transparent border-0">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-zinc-300">
              Avaliações Recentes
            </CardTitle>
            <Link
              href="/history"
              className="flex items-center gap-1 text-xs hover:underline"
              style={{ color: "#00e676" }}
            >
              Ver todas <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent>
            {recent === null ? (
              <RecentSkeletons />
            ) : recent.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-zinc-600">
                <InboxIcon className="h-8 w-8" />
                <p className="text-sm">Nenhuma avaliação ainda.</p>
                <Link href="/evaluate" className="text-xs hover:underline" style={{ color: "#00e676" }}>
                  Fazer a primeira avaliação →
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recent.map((ev) => (
                  <div key={ev.request_id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {ev.decision === "APPROVED" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                      )}
                      <div>
                        <p className="text-sm font-mono text-zinc-200">
                          #{ev.request_id.slice(0, 8)}
                        </p>
                        <p className="text-xs text-zinc-500">Score: {ev.score}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge
                        variant="outline"
                        className={
                          ev.decision === "APPROVED"
                            ? "border-emerald-700 text-emerald-400"
                            : "border-red-800 text-red-400"
                        }
                      >
                        {ev.decision === "APPROVED" ? "APROVADO" : "NEGADO"}
                      </Badge>
                      <p className="text-xs text-zinc-600 mt-1">
                        {new Date(ev.created_at).toLocaleDateString("pt-BR")}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tier distribution */}
        <Card className="bg-transparent border-0">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-300">
              Distribuição por Tier de Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats === null && !statsError ? (
              <Skeleton className="h-48 w-full bg-zinc-800 rounded-lg" />
            ) : tierData.length === 0 || stats?.total_evaluations === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-zinc-600">
                <InboxIcon className="h-8 w-8" />
                <p className="text-sm">Sem dados ainda.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={tierData} margin={{ left: 0, right: 16 }}>
                  <CartesianGrid vertical={false} stroke="rgba(0,230,118,0.07)" />
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
                    contentStyle={{
                      background: "#0a120a",
                      border: "1px solid rgba(0,230,118,0.2)",
                      borderRadius: 8,
                      color: "#e8f5e9",
                    }}
                    labelStyle={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}
                    itemStyle={{ color: "#e8f5e9" }}
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
            )}
          </CardContent>
        </Card>
      </div>

      {/* Credit product tiers + design decisions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="bg-transparent border-0">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-300">
              Produtos de Crédito — Tiers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {[
                {
                  range: "Score 850+",
                  limit: "R$ 50.000",
                  rate: "1,5% a.m.",
                  type: "Longo prazo",
                  color: "border-emerald-700/50 bg-emerald-900/20",
                },
                {
                  range: "Score 700–849",
                  limit: "R$ 20.000",
                  rate: "2,5% a.m.",
                  type: "Longo prazo",
                  color: "border-blue-700/50 bg-blue-900/20",
                },
                {
                  range: "Score 550–699",
                  limit: "R$ 8.000",
                  rate: "4,0% a.m.",
                  type: "Curto prazo",
                  color: "border-yellow-700/50 bg-yellow-900/20",
                },
                {
                  range: "Score < 550",
                  limit: "R$ 2.000",
                  rate: "6,0% a.m.",
                  type: "Curto prazo",
                  color: "border-orange-700/50 bg-orange-900/20",
                },
              ].map((tier) => (
                <div
                  key={tier.range}
                  className={`rounded-lg border p-3 ${tier.color}`}
                >
                  <p className="text-xs font-semibold text-zinc-300">{tier.range}</p>
                  <p className="text-lg font-bold text-zinc-100 mt-1">{tier.limit}</p>
                  <p className="text-xs text-zinc-400">{tier.rate}</p>
                  <p className="text-xs text-zinc-500 mt-1">{tier.type}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-transparent border-0">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-300">
              Decisões de Design
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {DESIGN_DECISIONS.map((d, i) => (
              <div key={i}>
                <p className="text-sm font-medium text-zinc-200">{d.choice}</p>
                <p className="text-xs text-zinc-500 mt-0.5">{d.rationale}</p>
                {i < DESIGN_DECISIONS.length - 1 && (
                  <Separator className="mt-3 bg-zinc-800" />
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
