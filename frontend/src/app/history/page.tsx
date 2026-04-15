"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ShapChart } from "@/components/shap-chart";
import { api } from "@/lib/api";
import type { EvaluationSummary } from "@/types/api";
import {
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  InboxIcon,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 15;

type Filter = "all" | "APPROVED" | "DENIED";

function DecisionBadge({ decision }: { decision: string }) {
  return (
    <Badge
      variant="outline"
      className={
        decision === "APPROVED"
          ? "border-emerald-700 text-emerald-400"
          : "border-red-800 text-red-400"
      }
    >
      {decision === "APPROVED" ? "APROVADO" : "NEGADO"}
    </Badge>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = (score / 1000) * 100;
  const color =
    score >= 700 ? "bg-emerald-400" : score >= 550 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "text-sm font-semibold tabular-nums",
          score >= 700
            ? "text-emerald-400"
            : score >= 550
              ? "text-yellow-400"
              : "text-red-400"
        )}
      >
        {score}
      </span>
      <div className="w-20 h-1.5 rounded-full bg-zinc-700">
        <div
          className={cn("h-full rounded-full", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ExpandedRow({ ev }: { ev: EvaluationSummary }) {
  const factors = Object.entries(ev.shap_explanation.contributions)
    .map(([feature, contribution]) => ({
      feature,
      contribution: contribution as number,
      direction:
        (contribution as number) > 0 ? "increases_risk" : "decreases_risk",
    }))
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));

  const payload = ev.request_payload as Record<string, unknown>;

  return (
    <TableRow className="bg-zinc-800/40 hover:bg-zinc-800/40">
      <TableCell colSpan={6} className="p-4">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* SHAP chart */}
          <div>
            <p className="text-xs font-medium text-zinc-400 mb-3 uppercase tracking-wide">
              Explicação SHAP
            </p>
            <ShapChart factors={factors.slice(0, 8)} />
            <div className="mt-3 space-y-1">
              <div className="flex justify-between text-xs text-zinc-600">
                <span>Base value</span>
                <span className="font-mono">
                  {ev.shap_explanation.base_value?.toFixed(4) ?? "—"}
                </span>
              </div>
            </div>
          </div>

          {/* Input features + SHAP values */}
          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wide">
                Features de entrada
              </p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                {Object.entries(payload)
                  .filter(([, v]) => v != null)
                  .map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-xs text-zinc-500 font-mono truncate">{k}</span>
                      <span className="text-xs text-zinc-300 tabular-nums ml-2">
                        {String(v)}
                      </span>
                    </div>
                  ))}
              </div>
            </div>

            <Separator className="bg-zinc-700" />

            <div>
              <p className="text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wide">
                Valores SHAP (todos)
              </p>
              <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                {factors.map(({ feature, contribution }) => (
                  <div key={feature} className="flex justify-between">
                    <span className="text-xs text-zinc-500 font-mono">{feature}</span>
                    <span
                      className={cn(
                        "text-xs tabular-nums font-medium",
                        contribution > 0 ? "text-red-400" : "text-emerald-400"
                      )}
                    >
                      {contribution > 0 ? "+" : ""}
                      {contribution.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );
}

export default function HistoryPage() {
  const [items, setItems] = useState<EvaluationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.evaluations({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      const filtered =
        filter === "all"
          ? data.items
          : data.items.filter((i) => i.decision === filter);
      setItems(filtered);
      setTotal(filter === "all" ? data.total : filtered.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar histórico");
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Histórico</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Todas as avaliações de crédito processadas pelo sistema.
        </p>
      </div>

      <Card className="bg-transparent border-0">
        <CardHeader className="flex-row items-center justify-between gap-4">
          <CardTitle className="text-sm font-medium text-zinc-300">
            Avaliações
            {total > 0 && (
              <span className="ml-2 text-zinc-500 font-normal">
                ({total.toLocaleString("pt-BR")} total)
              </span>
            )}
          </CardTitle>
          {/* Filters */}
          <div className="flex items-center gap-1">
            {(["all", "APPROVED", "DENIED"] as Filter[]).map((f) => (
              <button
                key={f}
                onClick={() => {
                  setFilter(f);
                  setPage(0);
                  setExpanded(null);
                }}
                className={cn(
                  "rounded-md px-3 py-1 text-xs transition-colors",
                  filter === f
                    ? "bg-indigo-500/20 text-indigo-300"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                )}
              >
                {f === "all" ? "Todas" : f === "APPROVED" ? "Aprovadas" : "Negadas"}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {error ? (
            <div className="flex items-center gap-2 p-6 text-sm text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          ) : loading ? (
            <div className="space-y-0">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-6 py-4 border-b border-zinc-800">
                  <Skeleton className="h-4 w-20 bg-zinc-800" />
                  <Skeleton className="h-6 w-16 bg-zinc-800 rounded-full" />
                  <Skeleton className="h-4 w-12 bg-zinc-800" />
                  <Skeleton className="h-4 w-32 bg-zinc-800" />
                  <Skeleton className="h-4 w-24 bg-zinc-800 ml-auto" />
                </div>
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-16 text-zinc-600">
              <InboxIcon className="h-10 w-10" />
              <p className="text-sm">Nenhuma avaliação encontrada.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800 hover:bg-transparent">
                  <TableHead className="text-zinc-500 text-xs w-8" />
                  <TableHead className="text-zinc-500 text-xs">ID</TableHead>
                  <TableHead className="text-zinc-500 text-xs">Decisão</TableHead>
                  <TableHead className="text-zinc-500 text-xs">Score</TableHead>
                  <TableHead className="text-zinc-500 text-xs">PD%</TableHead>
                  <TableHead className="text-zinc-500 text-xs">Modelo</TableHead>
                  <TableHead className="text-zinc-500 text-xs text-right">Data</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((ev) => (
                  <Fragment key={ev.request_id}>
                    <TableRow
                      className="cursor-pointer transition-colors" style={{borderBottom:"1px solid rgba(0,230,118,0.06)"}} onMouseEnter={(e)=>{(e.currentTarget as HTMLElement).style.background="rgba(0,230,118,0.05)"}} onMouseLeave={(e)=>{(e.currentTarget as HTMLElement).style.background=""}}
                      onClick={() =>
                        setExpanded((prev) =>
                          prev === ev.request_id ? null : ev.request_id
                        )
                      }
                    >
                      <TableCell className="py-3 pl-6">
                        {expanded === ev.request_id ? (
                          <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-zinc-600" />
                        )}
                      </TableCell>
                      <TableCell className="py-3 font-mono text-xs text-zinc-400">
                        #{ev.request_id.slice(0, 8)}
                      </TableCell>
                      <TableCell className="py-3">
                        <DecisionBadge decision={ev.decision} />
                      </TableCell>
                      <TableCell className="py-3">
                        <ScoreBar score={ev.score} />
                      </TableCell>
                      <TableCell className="py-3 text-xs text-zinc-400 tabular-nums">
                        {(ev.probability_of_default * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell className="py-3 text-xs text-zinc-500 max-w-[140px] truncate">
                        {ev.model_used}
                      </TableCell>
                      <TableCell className="py-3 text-xs text-zinc-500 text-right">
                        {new Date(ev.created_at).toLocaleString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                    </TableRow>
                    {expanded === ev.request_id && <ExpandedRow ev={ev} />}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {!loading && items.length > 0 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-800">
              <p className="text-xs text-zinc-500">
                Página {page + 1} de {totalPages}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 0}
                  onClick={() => {
                    setPage((p) => p - 1);
                    setExpanded(null);
                  }}
                  className="border-zinc-700 text-zinc-400 hover:bg-zinc-800 h-7 px-2"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages - 1}
                  onClick={() => {
                    setPage((p) => p + 1);
                    setExpanded(null);
                  }}
                  className="border-zinc-700 text-zinc-400 hover:bg-zinc-800 h-7 px-2"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
