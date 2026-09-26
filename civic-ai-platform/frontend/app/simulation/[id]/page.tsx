"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import AgentCard, { agentEntriesFromOutput, type AgentEntry } from "@/components/AgentCard";
import ArbiterPanel from "@/components/ArbiterPanel";
import { getClusters, getSimulation, type Simulation } from "@/lib/api";

type AgentCardConfig = {
  title: string;
  icon: string;
  accentClass: string;
  outputKey: "citizen_advocate" | "evidence_agent" | "finance_agent" | "equity_agent";
  scoreField?: string;
  scoreSuffix?: string;
};

const AGENTS: AgentCardConfig[] = [
  { title: "Citizen Advocate", icon: "👨", accentClass: "border-orange-200", outputKey: "citizen_advocate", scoreField: "priority_score", scoreSuffix: "/10" },
  { title: "Evidence", icon: "📸", accentClass: "border-blue-200", outputKey: "evidence_agent", scoreField: "severity_score", scoreSuffix: "/10" },
  { title: "Finance", icon: "💰", accentClass: "border-emerald-200", outputKey: "finance_agent" },
  { title: "Equity", icon: "⚖️", accentClass: "border-violet-200", outputKey: "equity_agent", scoreField: "equity_priority_score", scoreSuffix: "/10" },
];

function financeEntries(output: unknown): AgentEntry[] {
  if (!output || typeof output !== "object" || !("data" in output)) return [];
  const result = output as { data?: Record<string, unknown>; status?: string; error?: string };
  const data = result.data;
  if (!data) return [{ label: "Budget assessment", status: result.status, error: result.error }];
  const requested = typeof data.total_requested === "number" ? data.total_requested.toFixed(2) : "—";
  const available = typeof data.total_available === "number" ? data.total_available.toFixed(2) : "—";
  const delta = typeof data.shortfall_or_surplus === "number" ? data.shortfall_or_surplus.toFixed(2) : "—";
  return [{
    label: "Budget assessment",
    score: `₹${requested} cr requested`,
    justification: `${data.justification ?? "No justification returned."} Available: ₹${available} cr · Shortfall/surplus: ₹${delta} cr.`,
    data,
    status: result.status,
    error: result.error,
  }];
}

export default function SimulationPage() {
  const params = useParams<{ id: string }>();
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [clusterLabels, setClusterLabels] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = Number(params.id);
    if (!Number.isInteger(id)) {
      setError("That simulation ID is not valid.");
      setLoading(false);
      return;
    }
    let active = true;
    Promise.all([getSimulation(id), getClusters().catch(() => [])])
      .then(([data, clusters]) => {
        if (!active) return;
        setSimulation(data);
        setClusterLabels(
          Object.fromEntries(
            clusters.map((cluster) => [cluster.cluster_id, cluster.representative_location]),
          ),
        );
      })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load this simulation."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [params.id]);

  if (loading) {
    return <div className="mx-auto max-w-6xl px-6 py-20"><div className="h-10 w-64 animate-pulse rounded-xl bg-slate-200" /><div className="mt-10 grid gap-5 md:grid-cols-2"><div className="h-64 animate-pulse rounded-3xl bg-white" /><div className="h-64 animate-pulse rounded-3xl bg-white" /></div></div>;
  }

  if (error || !simulation) {
    return <div className="mx-auto max-w-3xl px-6 py-20"><div className="rounded-3xl bg-red-50 p-8 text-red-700"><h1 className="text-2xl font-bold">Could not load simulation</h1><p className="mt-2 text-sm">{error ?? "No simulation data was returned."}</p><Link href="/dashboard" className="mt-6 inline-block font-bold underline">Back to dashboard</Link></div></div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <Link href="/dashboard" className="text-sm font-bold text-teal hover:text-ink">← Back to dashboard</Link>
          <p className="mt-8 text-xs font-bold uppercase tracking-[0.22em] text-coral">Simulation #{simulation.id}</p>
          <h1 className="mt-3 text-4xl font-bold text-ink">Four perspectives, one transparent debate.</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">The specialist reports below are inputs to the Arbiter, not an automated spending decision.</p>
        </div>
        <span className="rounded-full border border-teal/20 bg-teal/10 px-4 py-2 text-sm font-bold capitalize text-teal">{simulation.status ?? simulation.simulation_status ?? "complete"}</span>
      </div>

      <section className="mt-10 grid gap-5 md:grid-cols-2">
        {AGENTS.map((agent) => {
          const output = simulation[agent.outputKey];
          const entries = agent.outputKey === "finance_agent"
            ? financeEntries(output)
            : agentEntriesFromOutput(output, agent.scoreField ?? "", agent.scoreSuffix ?? "", agent.title);
          return <AgentCard key={agent.outputKey} title={agent.title} icon={agent.icon} accentClass={agent.accentClass} entries={entries} rawData={output} />;
        })}
      </section>

      <div className="mt-8">
        <ArbiterPanel
          output={simulation.arbiter}
          totalBudget={simulation.total_budget}
          agentNames={AGENTS.map((agent) => agent.title)}
          clusterLabels={clusterLabels}
        />
      </div>
    </div>
  );
}
