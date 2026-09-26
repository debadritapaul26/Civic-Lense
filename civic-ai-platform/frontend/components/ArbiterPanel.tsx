"use client";

import type { AgentOutput, ArbiterData } from "@/lib/api";
import BudgetChart, { type BudgetAllocation } from "@/components/BudgetChart";

type ArbiterPanelProps = {
  output: AgentOutput;
  totalBudget?: number;
  agentNames?: string[];
  clusterLabels?: Record<string, string>;
};

function arbiterData(output: AgentOutput): ArbiterData | null {
  if (!output || typeof output !== "object" || !("data" in output)) return null;
  const data = output.data;
  if (!data || typeof data !== "object") return null;
  if (typeof data.explanation !== "string" || typeof data.confidence_score !== "number") {
    return null;
  }
  return {
    allocations:
      data.allocations && typeof data.allocations === "object"
        ? (data.allocations as Record<string, number>)
        : {},
    confidence_score: data.confidence_score,
    explanation: data.explanation,
  };
}

function highlightNames(text: string, names: string[]) {
  const escaped = names
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
    .map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (!escaped.length) return text;

  const matcher = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.split(matcher).map((part, index) =>
    names.some((name) => name.toLowerCase() === part.toLowerCase()) ? (
      <strong key={`${part}-${index}`} className="font-bold text-ink">
        {part}
      </strong>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    ),
  );
}

export default function ArbiterPanel({
  output,
  totalBudget,
  agentNames = [],
  clusterLabels = {},
}: ArbiterPanelProps) {
  const data = arbiterData(output);
  const allocationRows: BudgetAllocation[] = Object.entries(data?.allocations ?? {}).map(
    ([key, amount]) => ({
      label: clusterLabels[key] ?? key,
      amount,
    }),
  );
  const names = [
    ...Object.keys(data?.allocations ?? {}),
    "Citizen Advocate",
    "Evidence",
    "Finance",
    "Equity",
    ...agentNames,
  ];

  if (!data) {
    return (
      <section className="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-700">
        <h2 className="text-xl font-bold">⚖️ Arbiter unavailable</h2>
        <p className="mt-2 text-sm leading-6">
          The simulation did not return a validated final recommendation. Review the agent reports above before drawing conclusions.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-3xl border border-ink/10 bg-white p-6 shadow-soft sm:p-8">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-coral">Final synthesis</p>
          <h2 className="mt-2 text-2xl font-bold text-ink">⚖️ Arbiter recommendation</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Recommendation for human policymakers. This system does not execute or finalize government spending decisions.
          </p>
        </div>
        <div className="rounded-2xl bg-teal/10 px-5 py-4 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-teal">Confidence</p>
          <p className="mt-1 text-3xl font-bold text-ink">{data.confidence_score.toFixed(0)}%</p>
        </div>
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-bold text-ink">Location allocations</h3>
            {typeof totalBudget === "number" && (
              <span className="text-xs text-slate-500">Budget: ₹{totalBudget.toFixed(2)} cr</span>
            )}
          </div>
          <BudgetChart allocations={allocationRows} />
        </div>
        <div className="rounded-2xl bg-mist p-5">
          <h3 className="font-bold text-ink">Why this recommendation?</h3>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            {highlightNames(data.explanation, names)}
          </p>
        </div>
      </div>
    </section>
  );
}
