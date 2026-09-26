"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useRouter } from "next/navigation";
import UrgencyPriorityPanel from "@/components/UrgencyPriorityPanel";
import CivicDataOverview from "@/components/CivicDataOverview";
import {
  getClusters,
  runSimulation,
  type LocationCluster,
} from "@/lib/api";
import { CHART_COLORS } from "@/lib/chartColors";

const LocationMap = dynamic(() => import("@/components/LocationMap"), {
  ssr: false,
});

const PAGE_SIZE = 6;

function clusterCategoryData(cluster: LocationCluster) {
  return Object.entries(cluster.category_breakdown ?? {})
    .sort(([, first], [, second]) => second - first)
    .map(([category, complaints]) => ({
      category: category.length > 12 ? `${category.slice(0, 12)}…` : category,
      complaints,
    }));
}

function ClusterCardSkeleton() {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-4">
        <div className="h-6 w-3/4 animate-pulse rounded bg-slate-200" />
        <div className="h-5 w-5 animate-pulse rounded bg-slate-200" />
      </div>
      <div className="mt-5 grid grid-cols-3 gap-3">
        {[1, 2, 3].map((item) => <div key={item} className="h-12 animate-pulse rounded-2xl bg-mist" />)}
      </div>
      <div className="mt-5 h-24 animate-pulse rounded-2xl bg-mist" />
    </div>
  );
}

function ClusterCard({
  cluster,
  selected,
  active,
  onToggle,
}: {
  cluster: LocationCluster;
  selected: boolean;
  active: boolean;
  onToggle: () => void;
}) {
  const categoryData = clusterCategoryData(cluster);
  const evidencePct = Math.max(0, Math.min(100, cluster.evidence_verified_pct));

  return (
    <article
      id={`cluster-${cluster.cluster_id}`}
      className={`rounded-3xl border bg-white p-5 shadow-soft transition ${
        active ? "border-coral ring-4 ring-coral/10" : "border-slate-200"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wider text-coral">Location cluster</p>
          <h3 className="mt-1 truncate text-lg font-bold text-ink" title={cluster.representative_location}>
            {cluster.representative_location}
          </h3>
        </div>
        <label className="flex shrink-0 cursor-pointer items-center gap-2 text-xs font-bold text-slate-500">
          <span className="sr-only">Include {cluster.representative_location} in simulation</span>
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            className="h-5 w-5 rounded border-slate-300 text-teal accent-teal focus:ring-teal"
          />
          Include
        </label>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3 text-center">
        <div className="rounded-2xl bg-mist px-2 py-3">
          <p className="text-lg font-bold text-ink">{cluster.complaint_count}</p>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Complaints</p>
        </div>
        <div className="rounded-2xl bg-mist px-2 py-3">
          <p className="text-lg font-bold text-ink">{cluster.avg_urgency_score.toFixed(1)}</p>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Urgency</p>
        </div>
        <div className="rounded-2xl bg-mist px-2 py-3">
          <p className="text-lg font-bold text-ink">{evidencePct.toFixed(0)}%</p>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Evidence</p>
        </div>
      </div>

      <div className="mt-5">
        <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Category mix</p>
        {categoryData.length ? (
          <div className="h-24 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={categoryData}
                margin={{ top: 0, right: 8, left: 0, bottom: 0 }}
              >
                <XAxis type="number" hide allowDecimals={false} />
                <YAxis type="category" dataKey="category" width={72} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: CHART_COLORS.ink }} />
                <Tooltip cursor={{ fill: CHART_COLORS.mist }} formatter={(value: number) => [value, "Complaints"]} />
                <Bar
                  dataKey="complaints"
                  fill={CHART_COLORS.teal}
                  radius={[0, 5, 5, 0]}
                  barSize={12}
                  isAnimationActive
                  animationBegin={100}
                  animationDuration={750}
                  animationEasing="ease-out"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="rounded-xl bg-mist px-3 py-4 text-xs text-slate-500">No category data yet.</p>
        )}
      </div>
    </article>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [clusters, setClusters] = useState<LocationCluster[]>([]);
  const [selectedClusterIds, setSelectedClusterIds] = useState<string[]>([]);
  const [activeClusterId, setActiveClusterId] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [budget, setBudget] = useState("100");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let active = true;
    getClusters()
      .then((data) => {
        if (!active) return;
        setClusters(data);
        setSelectedClusterIds(data.map((cluster) => cluster.cluster_id));
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load location clusters.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleClusters = useMemo(
    () => (showAll ? clusters : clusters.slice(0, PAGE_SIZE)),
    [clusters, showAll],
  );
  const allSelected = clusters.length > 0 && selectedClusterIds.length === clusters.length;
  const markers = clusters.map((cluster) => ({
    id: cluster.cluster_id,
    latitude: cluster.latitude,
    longitude: cluster.longitude,
    label: `${cluster.representative_location} · ${cluster.complaint_count} complaints`,
  }));

  function toggleCluster(clusterId: string) {
    setSelectedClusterIds((current) =>
      current.includes(clusterId)
        ? current.filter((id) => id !== clusterId)
        : [...current, clusterId],
    );
  }

  function selectAllClusters() {
    setSelectedClusterIds(allSelected ? [] : clusters.map((cluster) => cluster.cluster_id));
  }

  function focusCluster(clusterId: string) {
    setActiveClusterId(clusterId);
    const clusterIndex = clusters.findIndex((cluster) => cluster.cluster_id === clusterId);
    if (!showAll && clusterIndex >= PAGE_SIZE) {
      setShowAll(true);
      window.setTimeout(() => {
        document.getElementById(`cluster-${clusterId}`)?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }, 50);
      return;
    }
    document.getElementById(`cluster-${clusterId}`)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }

  async function handleSimulation() {
    const totalBudget = Number(budget);
    if (!Number.isFinite(totalBudget) || totalBudget < 0) {
      setError("Enter a valid non-negative simulation budget.");
      return;
    }
    if (!selectedClusterIds.length) {
      setError("Select at least one location cluster for the simulation.");
      return;
    }

    setError(null);
    setRunning(true);
    try {
      const result = await runSimulation(selectedClusterIds, totalBudget);
      const simulationId = result.simulation_id ?? result.id;
      if (!simulationId) throw new Error("The server did not return a simulation ID.");
      router.push(`/simulation/${simulationId}`);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not run the simulation.");
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
      <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
        <div>
          <Link href="/report" className="text-sm font-bold text-teal hover:text-ink">← Submit another complaint</Link>
          <p className="mt-8 text-xs font-bold uppercase tracking-[0.22em] text-coral">Location overview</p>
          <h1 className="mt-3 text-4xl font-bold text-ink">A shared picture of need.</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
            Map-pinned complaints are grouped into nearby location clusters so the agents can debate urgency, evidence, budget, and equity around real places.
          </p>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:min-w-[320px]">
          <label htmlFor="budget" className="block text-xs font-bold uppercase tracking-wider text-slate-500">
            Simulation budget (₹ crore)
          </label>
          <div className="mt-3 flex gap-3">
            <input
              id="budget"
              type="number"
              min="0"
              step="0.01"
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
              className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-mist px-3 py-2 text-sm font-bold outline-none focus:border-teal focus:ring-4 focus:ring-teal/10"
            />
            <button
              type="button"
              onClick={handleSimulation}
              disabled={running || loading || !selectedClusterIds.length}
              className="rounded-xl bg-ink px-4 py-2 text-sm font-bold text-white transition hover:bg-teal disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {running ? "Running…" : "Run simulation"}
            </button>
          </div>
        </div>
      </div>

      {error && <p className="mt-8 rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-600">{error}</p>}

      <section className="mt-8"><CivicDataOverview /></section>

      <section className="mt-10">
        <UrgencyPriorityPanel />
      </section>

      <section className="mt-10" aria-labelledby="location-clusters-heading">
        <div className="mb-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal">Map-driven aggregation</p>
            <h2 id="location-clusters-heading" className="mt-2 text-2xl font-bold text-ink">Location clusters</h2>
            <p className="mt-2 text-sm text-slate-600">Select the places you want the agents to include in the next simulation.</p>
          </div>
          {clusters.length > 0 && (
            <button type="button" onClick={selectAllClusters} className="text-sm font-bold text-teal hover:text-ink">
              {allSelected ? "Clear all" : "Select all"}
            </button>
          )}
        </div>

        {loading ? (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((item) => <ClusterCardSkeleton key={item} />)}
          </div>
        ) : !clusters.length ? (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
            No location clusters yet — submit a complaint with a pinned location to get started.
          </div>
        ) : (
          <>
            <div className="mb-6 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                <div className="mb-4 flex items-center justify-between gap-4">
                  <div>
                    <h3 className="font-bold text-ink">Cluster map</h3>
                    <p className="mt-1 text-xs text-slate-500">Click a marker to highlight its card.</p>
                  </div>
                  <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-bold text-teal">{clusters.length} locations</span>
                </div>
                <LocationMap
                  markers={markers}
                  height={330}
                  activeMarkerId={activeClusterId}
                  emptyMessage="No pinned locations yet"
                  onMarkerClick={(marker) => marker.id && focusCluster(marker.id)}
                />
              </div>
              <div className="rounded-3xl border border-slate-200 bg-mist p-6">
                <p className="text-xs font-bold uppercase tracking-wider text-coral">Simulation scope</p>
                <p className="mt-3 text-4xl font-bold text-ink">{selectedClusterIds.length}</p>
                <p className="mt-1 text-sm text-slate-600">of {clusters.length} location clusters selected</p>
                <div className="mt-6 h-3 overflow-hidden rounded-full bg-white">
                  <div className="h-full rounded-full bg-teal transition-all" style={{ width: `${clusters.length ? (selectedClusterIds.length / clusters.length) * 100 : 0}%` }} />
                </div>
                <p className="mt-5 text-sm leading-6 text-slate-600">Use the checkboxes to focus the debate on a subset of hotspots, or leave every cluster selected for a full map-wide recommendation.</p>
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {visibleClusters.map((cluster) => (
                <ClusterCard
                  key={cluster.cluster_id}
                  cluster={cluster}
                  selected={selectedClusterIds.includes(cluster.cluster_id)}
                  active={activeClusterId === cluster.cluster_id}
                  onToggle={() => toggleCluster(cluster.cluster_id)}
                />
              ))}
            </div>
            {clusters.length > PAGE_SIZE && (
              <button
                type="button"
                onClick={() => setShowAll((current) => !current)}
                className="mt-6 w-full rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-teal transition hover:border-teal hover:bg-teal/5"
              >
                {showAll ? "Show fewer clusters" : `Show all ${clusters.length} clusters`}
              </button>
            )}
          </>
        )}
      </section>
    </div>
  );
}
