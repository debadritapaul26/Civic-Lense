"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getSimulationHistory, type SimulationHistoryItem } from "@/lib/api";

function HistorySkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((item) => (
        <div key={item} className="h-20 animate-pulse rounded-2xl bg-white" />
      ))}
    </div>
  );
}

export default function SimulationHistoryPage() {
  const [simulations, setSimulations] = useState<SimulationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getSimulationHistory()
      .then((data) => {
        if (active) setSimulations(data);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load simulation history.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-6 py-12 sm:py-16">
      <p className="text-xs font-bold uppercase tracking-[0.22em] text-coral">Reviewable decisions</p>
      <h1 className="mt-3 text-4xl font-bold text-ink">Simulation history</h1>
      <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
        Revisit previous multi-agent debates and see how recommendations changed over time.
      </p>

      <section className="mt-10">
        {loading ? (
          <HistorySkeleton />
        ) : error ? (
          <div className="rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-600">{error}</div>
        ) : !simulations.length ? (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <h2 className="font-bold text-ink">No simulations yet</h2>
            <p className="mt-2 text-sm text-slate-500">Run a location-cluster simulation from the dashboard to create the first record.</p>
            <Link href="/dashboard" className="mt-5 inline-flex rounded-xl bg-teal px-4 py-2 text-sm font-bold text-white hover:bg-ink">
              Open dashboard
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {simulations.map((simulation) => (
              <Link
                key={simulation.id}
                href={`/simulation/${simulation.id}`}
                className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:border-teal/40"
              >
                <div>
                  <p className="font-bold text-ink">Simulation #{simulation.id}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    Budget ₹{simulation.total_budget.toFixed(2)} crore
                    {simulation.created_at ? ` · ${new Date(simulation.created_at).toLocaleDateString("en-GB")}` : ""}
                  </p>
                </div>
                <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-bold capitalize text-teal">{simulation.status}</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
