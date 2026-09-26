"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getTopUrgencyLocations,
  type TopUrgencyLocation,
} from "@/lib/api";
import { CHART_COLORS } from "@/lib/chartColors";
import {
  evidenceConfidenceClass,
  evidenceConfidenceLabel,
  formatEvidenceAge,
} from "@/lib/evidence";

const LocationMap = dynamic(() => import("@/components/LocationMap"), {
  ssr: false,
});

const CATEGORY_ICONS: Record<string, string> = { road: "R", water: "W", healthcare: "H", electricity: "E", garbage: "G", "public transport": "T", safety: "S", drainage: "D", other: "•" };

function categoryIcon(category: string): string {
  return CATEGORY_ICONS[category.trim().toLowerCase()] ?? CATEGORY_ICONS.other;
}

function shortLocationName(location: string): string {
  return location.length > 28 ? `${location.slice(0, 28)}…` : location;
}

function UrgencyPrioritySkeleton() {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="h-72 animate-pulse rounded-2xl bg-mist" />
        <div className="h-72 animate-pulse rounded-2xl bg-mist" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {[1, 2, 3].map((item) => (
          <div key={item} className="rounded-2xl border border-slate-100 bg-mist p-5">
            <div className="h-5 w-3/4 animate-pulse rounded bg-slate-200" />
            <div className="mt-5 h-3 w-full animate-pulse rounded bg-slate-200" />
            <div className="mt-5 space-y-2">
              <div className="h-3 w-full animate-pulse rounded bg-slate-200" />
              <div className="h-3 w-5/6 animate-pulse rounded bg-slate-200" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function UrgencyPriorityPanel() {
  const [locations, setLocations] = useState<TopUrgencyLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getTopUrgencyLocations(3)
      .then((data) => {
        if (active) setLocations(data);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not load priority locations.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const sortedLocations = useMemo(
    () => [...locations].sort((a, b) => b.avg_urgency_score - a.avg_urgency_score),
    [locations],
  );

  const chartData = sortedLocations.map((location) => ({
    name: shortLocationName(location.representative_location),
    urgency: location.avg_urgency_score,
  }));

  const mapMarkers = sortedLocations.flatMap((location) => {
    if (
      typeof location.representative_latitude !== "number" ||
      typeof location.representative_longitude !== "number"
    ) {
      return [];
    }
    return [{
      latitude: location.representative_latitude,
      longitude: location.representative_longitude,
      label: `${location.representative_location} · ${location.category} · ${location.complaint_count} reports · urgency ${location.avg_urgency_score.toFixed(1)}/10 · evidence ${location.evidence_verified_pct.toFixed(0)}%`,
      color: location.avg_urgency_score >= 7 ? "#b84e3e" : location.avg_urgency_score >= 4 ? "#c49a42" : "#117d78",
    }];
  });

  return (
    <section id="priority-locations" className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft sm:p-8">
      <div className="mb-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-coral">Location-level urgency</p>
          <h2 className="mt-2 text-2xl font-bold text-ink">Top priority locations</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Nearby complaints are clustered by category so repeated reports of the same hotspot are visible together.
          </p>
        </div>
        <span className="rounded-full bg-coral/10 px-3 py-1 text-xs font-bold text-coral">Top 3 hotspots</span>
      </div>

      {loading ? (
        <UrgencyPrioritySkeleton />
      ) : error ? (
        <div className="rounded-2xl bg-red-50 px-5 py-4 text-sm text-red-600">{error}</div>
      ) : !sortedLocations.length ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-mist p-10 text-center text-sm text-slate-500">
          No pinned complaint locations are available yet.
        </div>
      ) : (
        <>
          <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={chartData}
                  margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
                >
                  <CartesianGrid stroke={CHART_COLORS.grid} horizontal={false} />
                  <XAxis
                    type="number"
                    domain={[0, 10]}
                    ticks={[0, 2, 4, 6, 8, 10]}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={150}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: CHART_COLORS.ink, fontSize: 12 }}
                  />
                  <Tooltip
                    cursor={{ fill: CHART_COLORS.mist }}
                    formatter={(value: number) => [`${value.toFixed(1)}/10`, "Avg urgency"]}
                  />
                  <Bar
                    dataKey="urgency"
                    fill={CHART_COLORS.coral}
                    radius={[0, 8, 8, 0]}
                    barSize={28}
                    isAnimationActive
                    animationBegin={150}
                    animationDuration={850}
                    animationEasing="ease-out"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <LocationMap markers={mapMarkers} height={288} />
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {sortedLocations.map((location) => {
              const evidencePct = Math.max(0, Math.min(100, location.evidence_verified_pct));
              const confidenceLabel = evidenceConfidenceLabel(evidencePct);
              return (
                <article key={`${location.representative_location}-${location.category}`} className="rounded-2xl border border-slate-100 bg-mist p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{location.category}</p>
                      <h3 className="mt-1 font-bold leading-5 text-ink">{location.representative_location}</h3>
                    </div>
                    <span className="text-2xl" aria-label={location.category}>{categoryIcon(location.category)}</span>
                  </div>
                  <div className="mt-5 flex items-center justify-between text-xs font-semibold text-slate-600">
                    <span>{location.complaint_count} complaints</span>
                    <span>{location.avg_urgency_score.toFixed(1)}/10 urgency</span>
                  </div>
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span className="flex items-center gap-1.5">
                        Evidence verified
                        <span
                          title={confidenceLabel}
                          aria-label={confidenceLabel}
                          className={`h-2 w-2 rounded-full ${evidenceConfidenceClass(evidencePct)}`}
                        />
                      </span>
                      <span className="font-bold text-ink">{evidencePct.toFixed(0)}%</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                      <div className="h-full rounded-full bg-teal transition-all" style={{ width: `${evidencePct}%` }} />
                    </div>
                  </div>
                  <p className="mt-4 text-xs font-semibold text-teal">
                    {formatEvidenceAge(location.most_recent_evidence_age_hours)}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{location.reasoning}</p>
                  <p className="mt-3 text-xs font-semibold text-ink">Suggested action: review recurring {location.category.toLowerCase()} reports and verify the site.</p>
                </article>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
