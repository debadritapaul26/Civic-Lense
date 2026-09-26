"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import BudgetChart, { type BudgetAllocation } from "@/components/BudgetChart";
import {
  getSimulation,
  getSimulationHistory,
  type AgentOutput,
  type AgentResult,
  type ArbiterData,
  type Simulation,
} from "@/lib/api";

type AreaScores = { label: string; urgency?: number; evidence?: number; equity?: number };
type DataRecord = Record<string, unknown>;

function results(output: AgentOutput | undefined): AgentResult[] {
  if (!output) return [];
  return "results" in output ? output.results : [output];
}
function dataOf(output: AgentOutput | undefined): DataRecord | null {
  if (!output || !("data" in output) || !output.data || typeof output.data !== "object") return null;
  return output.data as DataRecord;
}
function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

export default function RecommendationPage() {
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    getSimulationHistory(1)
      .then((history) => history[0] && getSimulation(history[0].id).then(setSimulation))
      .catch(() => undefined);
  }, []);

  const arbiter = dataOf(simulation?.arbiter) as Partial<ArbiterData> | null;
  const finance = dataOf(simulation?.finance_agent);
  const areaScores = useMemo(() => {
    const scores = new Map<string, AreaScores>();
    const add = (output: AgentOutput | undefined, field: "urgency" | "evidence" | "equity", scoreKey: string) => {
      for (const result of results(output)) {
        const id = result.cluster_id ?? String(result.data?.cluster ?? result.data?.cluster_or_complaint_id ?? "area");
        const details = (result.data ?? {}) as DataRecord;
        const existing = scores.get(id) ?? { label: String(details.cluster ?? details.cluster_or_complaint_id ?? id) };
        const score = numberValue(details[scoreKey]);
        scores.set(id, { ...existing, [field]: score });
      }
    };
    add(simulation?.citizen_advocate, "urgency", "priority_score");
    add(simulation?.evidence_agent, "evidence", "confidence_percent");
    add(simulation?.equity_agent, "equity", "equity_priority_score");
    return scores;
  }, [simulation]);

  const allocations = Object.entries(arbiter?.allocations ?? {}).map(([id, amount]) => {
    const scores = areaScores.get(id);
    return { id, label: scores?.label ?? id, amount, urgency: scores?.urgency, evidence: scores?.evidence, equity: scores?.equity };
  }).sort((a, b) => b.amount - a.amount);
  const chartRows: BudgetAllocation[] = allocations.map(({ label, amount }) => ({ label, amount }));
  const totalAllocated = allocations.reduce((sum, item) => sum + item.amount, 0);
  const proposed = numberValue(finance?.total_requested) ?? 0;
  const totalBudget = simulation?.total_budget ?? 0;
  const budgetGap = Math.max(0, proposed - totalBudget);
  const savings = Math.max(0, proposed - totalAllocated);

  if (!simulation) {
    return <div className="mx-auto max-w-6xl px-5 py-14 sm:px-8"><p className="text-xs font-bold uppercase tracking-[.22em] text-[#117d78]">Human-reviewed decision support</p><h1 className="mt-3 text-4xl font-bold text-[#12243a]">Final recommendation</h1><div className="mt-8 rounded-3xl border border-dashed bg-white p-10 text-center">No simulation available yet. <Link href="/dashboard" className="font-bold text-[#117d78]">Open Civic Data →</Link></div></div>;
  }

  return <div className="mx-auto max-w-6xl px-5 py-14 sm:px-8">
    <p className="text-xs font-bold uppercase tracking-[.22em] text-[#117d78]">Human-reviewed decision support</p>
    <h1 className="mt-3 text-4xl font-bold text-[#12243a] sm:text-5xl">Final recommendation</h1>
    <p className="mt-4 max-w-2xl leading-7 text-slate-600">A transparent, area-level allocation from the latest simulation. Recommendations support human review and do not authorize spending.</p>
    <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {[
        ["Total allocated", `INR ${totalAllocated.toFixed(2)} cr`],
        ["Original proposal", `INR ${proposed.toFixed(2)} cr`],
        ["Budget gap", `INR ${budgetGap.toFixed(2)} cr`],
        ["Optimized savings", `INR ${savings.toFixed(2)} cr`],
      ].map(([label, value]) => <article key={label} className="rounded-3xl border border-[#e4dfd3] bg-white p-5"><p className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</p><p className="mt-3 text-xl font-bold text-[#12243a]">{value}</p></article>)}
    </div>
    <section className="mt-6 rounded-3xl border border-[#e4dfd3] bg-white p-6 shadow-soft">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-bold text-[#12243a]">Recommended allocation by area</h2><p className="mt-1 text-sm text-slate-500">Ordered by allocated budget; scores are from the specialist agents.</p></div><span className="rounded-full bg-[#f4ecd9] px-3 py-1 text-xs font-bold text-[#876622]">Simulation #{simulation.id}</span></div>
      <div className="mt-5"><BudgetChart allocations={chartRows}/></div>
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500"><tr><th className="py-3 pr-4">Priority area</th><th className="py-3 pr-4">Allocation</th><th className="py-3 pr-4">Urgency</th><th className="py-3 pr-4">Evidence</th><th className="py-3">Equity</th></tr></thead><tbody>{allocations.map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="py-4 pr-4 font-semibold text-[#12243a]">{item.label}</td><td className="py-4 pr-4">INR {item.amount.toFixed(2)} cr</td><td className="py-4 pr-4">{item.urgency === undefined ? "—" : `${item.urgency.toFixed(1)}/10`}</td><td className="py-4 pr-4">{item.evidence === undefined ? "—" : `${item.evidence.toFixed(0)}%`}</td><td className="py-4">{item.equity === undefined ? "—" : `${item.equity.toFixed(1)}/10`}</td></tr>)}</tbody></table></div>
    </section>
    <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_auto]"><article className="rounded-3xl bg-[#12243a] p-7 text-white"><p className="text-xs font-bold uppercase tracking-wider text-[#d8b45e]">Agent summary</p><p className="mt-3 leading-7 text-white/85">{arbiter?.explanation ?? "No final Arbiter narrative was returned."}</p><p className="mt-3 text-xs text-white/60">Arbiter confidence: {numberValue(arbiter?.confidence_score)?.toFixed(0) ?? "—"}%</p></article><button onClick={() => setReady(true)} className="rounded-3xl border border-[#c49a42] bg-[#f5edda] px-7 py-5 text-left font-bold text-[#12243a]">Approve &amp; Forward to Government<small className="mt-2 block max-w-xs font-normal text-slate-600">Demo action only; no government office is connected.</small></button></div>
    {ready && <p role="status" className="mt-4 rounded-xl bg-[#e7f2ef] p-4 text-sm text-[#117d78]">Marked ready for human review in this demo.</p>}
  </div>;
}