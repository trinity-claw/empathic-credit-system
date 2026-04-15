"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ShapChart } from "@/components/shap-chart";
import { api } from "@/lib/api";
import type { CreditRequest, CreditResponse } from "@/types/api";
import { CheckCircle2, ChevronDown, ChevronUp, ExternalLink, Loader2, XCircle } from "lucide-react";

const FINANCIAL_DEFAULTS: CreditRequest = {
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

const FINANCIAL_LABELS: Array<{ key: keyof CreditRequest; label: string }> = [
  { key: "revolving_utilization", label: "Utilização rotativo (0–1)" },
  { key: "age", label: "Idade" },
  { key: "monthly_income", label: "Renda mensal (R$)" },
  { key: "debt_ratio", label: "Índice de endividamento" },
  { key: "open_credit_lines", label: "Linhas de crédito abertas" },
  { key: "real_estate_loans", label: "Empréstimos imobiliários" },
  { key: "past_due_30_59", label: "Atrasos 30–59 dias" },
  { key: "past_due_60_89", label: "Atrasos 60–89 dias" },
  { key: "past_due_90", label: "Atrasos > 90 dias" },
  { key: "dependents", label: "Dependentes" },
  { key: "had_past_due_sentinel", label: "Flag sentinela (0 ou 1)" },
];

const EMOTIONAL_LABELS: Array<{ key: keyof CreditRequest; label: string; hint: string }> = [
  { key: "stress_level", label: "Nível de estresse (0–1)", hint: "Capturado pelo sensor wearable" },
  { key: "impulsivity_score", label: "Score de impulsividade (0–1)", hint: "Deriva do padrão de gastos" },
  { key: "emotional_stability", label: "Estabilidade emocional (0–1)", hint: "Inverso do estresse crônico" },
  { key: "financial_stress_events_7d", label: "Eventos de estresse (7 dias)", hint: "Número de eventos nos últimos 7 dias" },
];

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
  const router = useRouter();
  const [form, setForm] = useState<CreditRequest>(FINANCIAL_DEFAULTS);
  const [showEmotional, setShowEmotional] = useState(false);
  const [result, setResult] = useState<CreditResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [offerAccepted, setOfferAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setOfferAccepted(false);
    try {
      const res = await api.evaluate(form);
      setResult(res);
      toast.success(
        res.decision === "APPROVED"
          ? `Crédito aprovado — Score ${res.score}`
          : `Crédito negado — Score ${res.score}`
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro desconhecido";
      setError(msg);
      toast.error("Erro na avaliação", { description: msg });
    } finally {
      setLoading(false);
    }
  }

  async function handleAcceptOffer() {
    if (!result?.offer_id) return;
    setAccepting(true);
    try {
      await api.acceptOffer(result.offer_id);
      setOfferAccepted(true);
      toast.success("Oferta aceita!", {
        description: "O crédito está sendo processado.",
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao aceitar oferta";
      toast.error("Falha ao aceitar oferta", { description: msg });
    } finally {
      setAccepting(false);
    }
  }

  function handleChange(key: keyof CreditRequest, value: string) {
    const parsed = value === "" ? null : parseFloat(value);
    setForm((prev) => ({ ...prev, [key]: parsed }));
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Avaliar Crédito</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Submete os dados do tomador e recebe score, decisão e explicação SHAP em tempo real.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
        {/* Form */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-300">
              Dados do Tomador
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                {FINANCIAL_LABELS.map(({ key, label }) => (
                  <div key={key} className="space-y-1.5">
                    <Label className="text-xs text-zinc-400">{label}</Label>
                    <Input
                      type="number"
                      step="any"
                      value={form[key] ?? ""}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className="bg-zinc-800 border-zinc-700 text-zinc-100 text-sm h-8 focus-visible:ring-indigo-500"
                    />
                  </div>
                ))}
              </div>

              <Separator className="bg-zinc-800" />

              {/* Emotional features toggle */}
              <button
                type="button"
                onClick={() => setShowEmotional((v) => !v)}
                className="flex w-full items-center justify-between text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <span>
                  Features emocionais{" "}
                  <span className="text-zinc-600">(opcional — ativa modelo emocional)</span>
                </span>
                {showEmotional ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>

              {showEmotional && (
                <div className="grid grid-cols-2 gap-4 rounded-lg bg-zinc-800/50 p-4 border border-zinc-800">
                  {EMOTIONAL_LABELS.map(({ key, label, hint }) => (
                    <div key={key} className="space-y-1.5">
                      <Label className="text-xs text-zinc-400">
                        {label}
                        <span className="block text-zinc-600 font-normal">{hint}</span>
                      </Label>
                      <Input
                        type="number"
                        step="any"
                        value={form[key] ?? ""}
                        onChange={(e) => handleChange(key, e.target.value)}
                        className="bg-zinc-800 border-zinc-700 text-zinc-100 text-sm h-8 focus-visible:ring-indigo-500"
                      />
                    </div>
                  ))}
                </div>
              )}

              {error && (
                <p className="text-sm text-red-400 rounded-lg bg-red-900/20 px-3 py-2">
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

        {/* Result */}
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
                        variant="outline"
                        className={
                          result.decision === "APPROVED"
                            ? "border-emerald-700 text-emerald-400"
                            : "border-red-800 text-red-400"
                        }
                      >
                        {result.decision === "APPROVED" ? "APROVADO" : "NEGADO"}
                      </Badge>
                    </div>
                    <p className={`text-5xl font-bold mt-3 tabular-nums ${scoreColor(result.score)}`}>
                      {result.score}
                    </p>
                    <p className="text-sm text-zinc-500 mt-1">{scoreLabel(result.score)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-zinc-500">PD (default)</p>
                    <p className="text-xl font-semibold text-zinc-200 tabular-nums mt-1">
                      {(result.probability_of_default * 100).toFixed(2)}%
                    </p>
                  </div>
                </div>

                {result.decision === "APPROVED" && (
                  <>
                    <Separator className="my-4 bg-zinc-800" />
                    <div className="grid grid-cols-3 gap-4 text-center mb-4">
                      <div>
                        <p className="text-xs text-zinc-500">Limite</p>
                        <p className="text-lg font-bold text-zinc-100">
                          R${" "}
                          {result.credit_limit.toLocaleString("pt-BR")}
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

                    {result.offer_id && !offerAccepted && (
                      <Button
                        onClick={handleAcceptOffer}
                        disabled={accepting}
                        className="w-full bg-emerald-700 hover:bg-emerald-600 text-white"
                      >
                        {accepting ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Processando…
                          </>
                        ) : (
                          "Aceitar Oferta de Crédito"
                        )}
                      </Button>
                    )}

                    {offerAccepted && (
                      <div className="rounded-lg bg-emerald-900/20 border border-emerald-800/50 px-3 py-2 text-sm text-emerald-400">
                        Oferta aceita — crédito sendo processado.
                      </div>
                    )}
                  </>
                )}

                <Separator className="my-4 bg-zinc-800" />
                <div className="grid grid-cols-2 gap-2 text-xs text-zinc-600">
                  <div>
                    <span className="text-zinc-500">Request ID: </span>
                    <span className="font-mono">{result.request_id.slice(0, 8)}…</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Modelo: </span>
                    <span>{result.model_used}</span>
                  </div>
                </div>
                <button
                  onClick={() => router.push("/history")}
                  className="mt-2 flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
                >
                  <ExternalLink className="h-3 w-3" />
                  Ver no histórico
                </button>
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
                <ShapChart factors={result.top_factors} />
              </CardContent>
            </Card>

            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-zinc-300">
                  Todos os Valores SHAP
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(result.shap_explanation.contributions)
                    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                    .map(([feature, value]) => (
                      <div key={feature} className="flex justify-between items-center">
                        <span className="text-xs text-zinc-400 font-mono">{feature}</span>
                        <span
                          className={`text-xs tabular-nums font-medium ${
                            value > 0 ? "text-red-400" : "text-emerald-400"
                          }`}
                        >
                          {value > 0 ? "+" : ""}
                          {value.toFixed(4)}
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
          <div className="flex flex-col items-center justify-center h-64 rounded-xl border border-dashed border-zinc-800 gap-2">
            <p className="text-sm text-zinc-600">O resultado aparece aqui após a avaliação</p>
            <p className="text-xs text-zinc-700">Preencha o formulário e clique em Avaliar</p>
          </div>
        )}
      </div>
    </div>
  );
}
