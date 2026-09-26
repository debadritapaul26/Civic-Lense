import type { AgentResult } from "@/lib/api";
import { formatUploadedTimestamp } from "@/lib/evidence";

export type AgentEntry = {
  label: string;
  score?: string;
  justification?: string;
  data?: Record<string, unknown>;
  status?: string;
  error?: string;
};

type AgentCardProps = {
  title: string;
  icon: string;
  accentClass: string;
  entries: AgentEntry[];
  rawData: unknown;
};

function resultEntries(output: unknown): AgentResult[] {
  if (!output || typeof output !== "object") return [];
  if ("results" in output && Array.isArray(output.results)) {
    return output.results as AgentResult[];
  }
  return [output as AgentResult];
}

export function agentEntriesFromOutput(
  output: unknown,
  scoreField: string,
  scoreSuffix: string,
  labelFallback: string,
): AgentEntry[] {
  return resultEntries(output).map((result, index) => {
    const data = result.data;
    const score = data?.[scoreField];
    const label =
      String(
        data?.cluster ??
          data?.cluster_or_complaint_id ??
          "",
      ) || result.cluster_id || labelFallback;
    return {
      label: `${label}${index > 0 && label === labelFallback ? ` ${index + 1}` : ""}`,
      score: typeof score === "number" ? `${score}${scoreSuffix}` : undefined,
      justification:
        typeof data?.justification === "string" ? data.justification : undefined,
      data,
      status: result.status,
      error: result.error,
    };
  });
}

export default function AgentCard({
  title,
  icon,
  accentClass,
  entries,
  rawData,
}: AgentCardProps) {
  return (
    <article className={`overflow-hidden rounded-3xl border bg-white shadow-soft ${accentClass}`}>
      <div className="flex items-center justify-between border-b border-inherit px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl" aria-hidden="true">
            {icon}
          </span>
          <h2 className="font-bold text-ink">{title}</h2>
        </div>
        <span className="rounded-full bg-white/70 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Agent report
        </span>
      </div>
      <div className="space-y-4 p-5">
        {entries.length ? (
          entries.map((entry, index) => (
            <div key={`${entry.label}-${index}`} className="rounded-2xl bg-mist p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="font-bold text-ink">{entry.label}</p>
                {entry.score && (
                  <span className="whitespace-nowrap rounded-full bg-white px-2.5 py-1 text-xs font-bold text-teal">
                    {entry.score}
                  </span>
                )}
              </div>
              {entry.status === "failed" ? (
                <p className="mt-3 text-sm text-red-600">
                  This agent could not return a usable result: {entry.error ?? "unknown error"}
                </p>
              ) : entry.justification ? (
                <p className="mt-3 text-sm leading-6 text-slate-600">{entry.justification}</p>
              ) : (
                <p className="mt-3 text-sm text-slate-500">No narrative justification returned.</p>
              )}
              {entry.data && (
                (() => {
                  const uploadedAt = entry.data.evidence_uploaded_at;
                  const ageHours = entry.data.evidence_age_hours;
                  const timestamp = formatUploadedTimestamp(
                    typeof uploadedAt === "string" ? uploadedAt : null,
                    typeof ageHours === "number" ? ageHours : null,
                  );
                  return timestamp ? (
                    <p className="mt-3 text-xs font-semibold text-slate-500">{timestamp}</p>
                  ) : null;
                })()
              )}
            </div>
          ))
        ) : (
          <p className="text-sm text-slate-500">No report was returned by this agent.</p>
        )}
        <details className="group rounded-2xl border border-slate-200 bg-white">
          <summary className="cursor-pointer list-none px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500 transition group-open:text-teal">
            <span className="mr-2">＋</span> Show raw JSON
          </summary>
          <pre className="max-h-64 overflow-auto border-t border-slate-100 px-4 py-3 text-xs leading-5 text-slate-600">
            {JSON.stringify(rawData, null, 2)}
          </pre>
        </details>
      </div>
    </article>
  );
}
