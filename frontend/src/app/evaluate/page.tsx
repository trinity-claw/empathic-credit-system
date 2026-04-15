"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ShapChart } from "@/components/shap-chart";
import { api } from "@/lib/api";
import type { CreditRequest, CreditResponse } from "@/types/api";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

const DEFAULT_VALUES: CreditRequest = {
  revolving_utilization: 0.3,
  age: 45,
  past_due_30_59: 0,
  debt_ratio: 0.25,
  monthly_income: 5000,
  open_credit_lines: 4,
  past_due_90: 0,
  real_estate_loans: 1,
  past_due_60_89: 0,
  dependents: 2,
  had_past_due_sentinel: 0,
};

const FIELD_LABELS: Record<keyof CreditRequest, string> = {
  revolving_utilization: "Utilização rotativo (0–1)",
  age: "Idade",
  past_due_30_59: "Atrasos 30–59 dias",
  debt_ratio: "Índice de endividamento",
  monthly_income: "Renda mensal (R$)",
  open_credit_lines: "Linhas de crédito abertas",
  past_due_90: "Atrasos > 90 dias",
  real_estate_loans: "Empréstimos imobiliários",
  past_due_60_89: "Atrasos 60–89 dias",
  dependents: "Dependentes",
  had_past_due_sentinel: "Flag sentinela (0 ou 1)",
};

function scoreColor(score: number) {
  if (score >= 700) return "text-emerald-400";
  if (score >= 550) return "text-yellow-400";
  return "text-red-400";
}

function scoreLabel(score: number) {
  if (score >= 850) return "Excelente";
  if (score >= 700) return "Bom";
  if (score >= 550) return "Regular";
  return "Alto risco";
}

export default function EvaluatePage() {
  const [form, setForm] = useState<CreditRequest>(DEFAULT_VALUES);
  const [result, setResult] = useState<CreditResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.evaluate(form);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }

  function handleChange(key: keyof CreditRequest, value: string) {
    setForm((prev) => ({ ...prev, [key]: parseFloat(value) || 0 }));
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Avaliar Crédito</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Submete os dados do tomador e recebe score, decisão e explicação SHAP em tempo real.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-300">
              Dados do Tomador
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {(Object.keys(DEFAULT_VALUES) as (keyof CreditRequest)[]).map((key) => (
                  <div key={key} className="space-y-1.5">
                    <Label className="text-xs text-zinc-400">{FIELD_LABELS[key]}</Label>
                    <Input
                      type="number"
                      step="any"
                      value={form[key]}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className="bg-zinc-800 border-zinc-700 text-zinc-100 text-sm h-8 focus-visible:ring-indigo-500"
                    />
                  </div>
                ))}
              </div>

              {error && (
                <p className="text-sm text-red-400 bg-red-900/20 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Avaliando…
                  </>
                ) : (
                  "Avaliar"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {result ? (
          <div className="space-y-5">
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      {result.decision === "APPROVED" ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-400" />
                      )}
                      <Badge
                        className={
                          result.decision === "APPROVED"
                            ? "bg-emerald-900/40 text-emerald-300 border-emerald-700"
                            : "bg-red-900/40 text-red-300 border-red-800"
                        }
                        variant="outline"
                      >
                        {result.decision === "APPROVED" ? "APROVADO" : "NEGADO"}
                      </Badge>
                    </div>
                    <p className={`text-5xl font-bold mt-3 tabular-nums ${scoreColor(result.score)}`}>
                      {result.score}
                    </p>
                    <p className="text-sm text-zinc-500 mt-1">{scoreLabel(result.score)}</p>
                  </div>
                  <div className="text-right space-y-2">
                    <p className="text-xs text-zinc-500">PD (probabilidade default)</p>
                    <p className="text-xl font-semibold text-zinc-200 tabular-nums">
                      {(result.probability_of_default * 100).toFixed(2)}%
                    </p>
                  </div>
                </div>

                {result.decision === "APPROVED" && (
                  <>
                    <Separator className="my-4 bg-zinc-800" />
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <p className="text-xs text-zinc-500">Limite</p>
                        <p className="text-lg font-bold text-zinc-100">
                          R$ {result.credit_limit.toLocaleString("pt-BR")}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Taxa mensal</p>
                        <p className="text-lg font-bold text-zinc-100">
                          {result.interest_rate != null
                            ? `${(result.interest_rate * 100).toFixed(1)}%`
                            : "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Tipo</p>
                        <p className="text-sm font-medium text-zinc-300 capitalize">
                          {result.credit_type?.replace("_", " ") ?? "—"}
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-zinc-300">
                  Explicação SHAP — Top Fatores
                </CardTitle>
                <p className="text-xs text-zinc-500">
                  Vermelho = aumenta risco · Verde = reduz risco
                </p>
              </CardHeader>
              <CardContent>
                <ShapChart factors={result.shap_explanation.top_factors} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-zinc-300">
                  Todos os Fatores SHAP
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(result.shap_explanation.shap_values)
                    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                    .map(([feature, value]) => (
                      <div key={feature} className="flex justify-between items-center">
                        <span className="text-xs text-zinc-400 font-mono">{feature}</span>
                        <span
                          className={`text-xs tabular-nums font-medium ${
                            value > 0 ? "text-red-400" : "text-emerald-400"
                          }`}
                        >
                          {value > 0 ? "+" : ""}{value.toFixed(4)}
                        </span>
                      </div>
                    ))}
                  <Separator className="bg-zinc-800 my-2" />
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-zinc-500">Base value</span>
                    <span className="text-xs text-zinc-400 tabular-nums">
                      {result.shap_explanation.base_value.toFixed(4)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 rounded-xl border border-dashed border-zinc-800">
            <p className="text-sm text-zinc-600">
              O resultado aparece aqui após a avaliação
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
