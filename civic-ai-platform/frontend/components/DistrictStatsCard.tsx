import type { DistrictStats } from "@/lib/api";
import {
  evidenceConfidenceClass,
  evidenceConfidenceLabel,
} from "@/lib/evidence";

type DistrictStatsCardProps = {
  stats: DistrictStats;
};

export function DistrictStatsCardSkeleton() {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
          <div className="h-6 w-36 animate-pulse rounded bg-slate-200" />
        </div>
        <div className="h-6 w-20 animate-pulse rounded-full bg-slate-200" />
      </div>
      <div className="mt-6 grid grid-cols-3 gap-3">
        {[1, 2, 3].map((item) => (
          <div key={item} className="rounded-2xl bg-mist p-3">
            <div className="h-3 w-16 animate-pulse rounded bg-slate-200" />
            <div className="mt-2 h-7 w-12 animate-pulse rounded bg-slate-200" />
          </div>
        ))}
      </div>
    </article>
  );
}

function districtName(stats: DistrictStats): string {
  return stats.district_name ?? stats.name ?? `District ${stats.district_id}`;
}

export default function DistrictStatsCard({
  stats,
}: DistrictStatsCardProps) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal">
            District {stats.district_id}
          </p>
          <h2 className="mt-1 text-xl font-bold text-ink">{districtName(stats)}</h2>
        </div>
        <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-bold text-teal">
          Live stats
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-2xl bg-mist p-3">
          <p className="text-xs text-slate-500">Complaints</p>
          <p className="mt-1 text-2xl font-bold text-ink">{stats.complaint_count}</p>
        </div>
        <div className="rounded-2xl bg-mist p-3">
          <p className="text-xs text-slate-500">Avg urgency</p>
          <p className="mt-1 text-2xl font-bold text-ink">
            {stats.avg_urgency.toFixed(1)}
            <span className="text-sm font-medium text-slate-400">/10</span>
          </p>
        </div>
        <div className="rounded-2xl bg-mist p-3">
          <p className="flex items-center gap-1.5 text-xs text-slate-500">
            Evidence
            <span
              title={evidenceConfidenceLabel(stats.evidence_verified_pct)}
              aria-label={evidenceConfidenceLabel(stats.evidence_verified_pct)}
              className={`h-2 w-2 rounded-full ${evidenceConfidenceClass(stats.evidence_verified_pct)}`}
            />
          </p>
          <p className="mt-1 text-2xl font-bold text-ink">
            {stats.evidence_verified_pct.toFixed(0)}
            <span className="text-sm font-medium text-slate-400">%</span>
          </p>
        </div>
      </div>
      {stats.complaint_count === 0 && (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-mist px-4 py-3 text-sm text-slate-500">
          No complaints reported yet for this district.
        </div>
      )}
    </article>
  );
}
