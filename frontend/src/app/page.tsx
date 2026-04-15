import { MetricCard } from "@/components/metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, XCircle } from "lucide-react";

const MODEL_METRICS = [
  { title: "AUC-ROC", value: "0.8676", subtitle: "Conjunto de teste (n=22.500)", trend: "up" as const },
  { title: "KS Statistic", value: "0.5764", subtitle: "Benchmark: KS > 0.40 → bom" },
  { title: "Brier Score", value: "0.0488", subtitle: "Após calibração isotônica", trend: "up" as const },
  { title: "Taxa de Default", value: "6.68%", subtitle: "150.000 tomadores — Give Me Some Credit" },
];

const RECENT_DECISIONS = [
  { id: "a1b2c3", decision: "APROVADO", score: 742, limit: "R$ 20.000", type: "Longo prazo" },
  { id: "d4e5f6", decision: "APROVADO", score: 851, limit: "R$ 50.000", type: "Longo prazo" },
  { id: "g7h8i9", decision: "NEGADO", score: 310, limit: "—", type: "—" },
  { id: "j0k1l2", decision: "APROVADO", score: 591, limit: "R$ 8.000", type: "Curto prazo" },
  { id: "m3n4o5", decision: "NEGADO", score: 488, limit: "—", type: "—" },
];

const DESIGN_DECISIONS = [
  { choice: "XGBoost + Isotonic Calibration", rationale: "AUC 0.87 vs 0.82 baseline. Calibração reduz Brier de 0.055 → 0.049." },
  { choice: "SHAP TreeExplainer (exato)", rationale: "Valores de Shapley exatos em O(TLD). Legalmente defensável para Art. 20 LGPD." },
  { choice: "Features emocionais: não deployadas", rationale: "Delta AUC = -0.0008. Custo regulatório (LGPD Art. 11) supera o benefício." },
  { choice: "SQLite + rq", rationale: "Zero ops. ACID. Migração para Postgres é uma variável de config." },
];

export default function DashboardPage() {
  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Empathic Credit System — XGBoost · SHAP · FastAPI
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {MODEL_METRICS.map((m) => (
          <MetricCard key={m.title} {...m} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-300">
              Decisões Recentes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {RECENT_DECISIONS.map((d) => (
              <div key={d.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {d.decision === "APROVADO" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                  )}
                  <div>
                    <p className="text-sm text-zinc-200 font-mono">#{d.id}</p>
                    <p className="text-xs text-zinc-500">Score: {d.score}</p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge
                    variant="outline"
                    className={
                      d.decision === "APROVADO"
                        ? "border-emerald-700 text-emerald-400"
                        : "border-red-800 text-red-400"
                    }
                  >
                    {d.decision}
                  </Badge>
                  {d.limit !== "—" && (
                    <p className="text-xs text-zinc-500 mt-1">{d.limit}</p>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-zinc-900 border-zinc-800">
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

      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-zinc-300">
            Produtos de Crédito — Tiers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              { range: "Score 850+", limit: "R$ 50.000", rate: "1,5% a.m.", type: "Longo prazo", color: "border-emerald-700/50 bg-emerald-900/20" },
              { range: "Score 700–849", limit: "R$ 20.000", rate: "2,5% a.m.", type: "Longo prazo", color: "border-blue-700/50 bg-blue-900/20" },
              { range: "Score 550–699", limit: "R$ 8.000", rate: "4,0% a.m.", type: "Curto prazo", color: "border-yellow-700/50 bg-yellow-900/20" },
              { range: "Score < 550", limit: "R$ 2.000", rate: "6,0% a.m.", type: "Curto prazo", color: "border-orange-700/50 bg-orange-900/20" },
            ].map((tier) => (
              <div key={tier.range} className={`rounded-lg border p-3 ${tier.color}`}>
                <p className="text-xs font-semibold text-zinc-300">{tier.range}</p>
                <p className="text-lg font-bold text-zinc-100 mt-1">{tier.limit}</p>
                <p className="text-xs text-zinc-400">{tier.rate}</p>
                <p className="text-xs text-zinc-500 mt-1">{tier.type}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
