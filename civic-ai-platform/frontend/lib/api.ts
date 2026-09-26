export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export type DistrictStats = {
  district_id: number;
  district_name?: string;
  name?: string;
  complaint_count: number;
  avg_urgency: number;
  evidence_verified_pct: number;
  category_breakdown?: Record<string, number>;
};

export type LocationCluster = {
  cluster_id: string;
  representative_location: string;
  latitude: number;
  longitude: number;
  complaint_count: number;
  avg_urgency_score: number;
  evidence_verified_pct: number;
  category_breakdown: Record<string, number>;
  most_recent_evidence_age_hours?: number | null;
};

export type LocationClusterDetail = LocationCluster & {
  complaints: Complaint[];
};

export type Complaint = {
  id: number;
  raw_text: string;
  language_detected: string;
  problem?: string | null;
  category: string;
  urgency_score: number;
  location_hint?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  formatted_address?: string | null;
  district_id?: number | null;
  evidence_file_path?: string | null;
  evidence_uploaded_at?: string | null;
  evidence_age_hours?: number | null;
  created_at: string;
};

export type TopUrgencyLocation = {
  representative_location: string;
  representative_latitude?: number | null;
  representative_longitude?: number | null;
  complaint_count: number;
  avg_urgency_score: number;
  evidence_verified_pct: number;
  most_recent_evidence_age_hours?: number | null;
  category: string;
  district_id?: number | null;
  reasoning: string;
};

export type SimulationRequest = {
  cluster_ids?: string[];
  total_budget: number;
  equity_context?: Record<string, Record<string, unknown>>;
};

export type AgentData = Record<string, unknown>;

export type AgentResult = {
  agent: string;
  status: "success" | "failed" | string;
  data?: AgentData;
  error?: string;
  cluster_id?: string;
  district_id?: number;
};

export type AgentOutput = AgentResult | { results: AgentResult[] } | null;

export type ArbiterData = {
  allocations: Record<string, number>;
  confidence_score: number;
  explanation: string;
};

export type Simulation = {
  id: number;
  total_budget: number;
  citizen_advocate: AgentOutput;
  evidence_agent: AgentOutput;
  finance_agent: AgentOutput;
  equity_agent: AgentOutput;
  arbiter: AgentOutput;
  simulation_status?: string;
  status?: string;
  simulation_id?: number;
  created_at?: string;
  error?: string;
};

export type SimulationHistoryItem = {
  id: number;
  total_budget: number;
  status: string;
  created_at?: string;
};

export type SubmitComplaintInput = {
  text: string;
  latitude: number;
  longitude: number;
  formatted_address: string;
  file?: File | null;
};

export type LocationSearchResult = {
  display_name: string;
  latitude: number;
  longitude: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Cannot connect to the backend at ${API_BASE_URL}. Start FastAPI with ` +
        `"uvicorn main:app --reload" from civic-ai-platform/backend.`,
      { cause: error },
    );
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the useful status-based message when the server did not return JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export async function submitComplaint(
  input: SubmitComplaintInput,
): Promise<Complaint> {
  const formData = new FormData();
  formData.append("text", input.text);
  formData.append("latitude", String(input.latitude));
  formData.append("longitude", String(input.longitude));
  formData.append("formatted_address", input.formatted_address);
  if (input.file) formData.append("file", input.file);

  return request<Complaint>("/complaints", {
    method: "POST",
    body: formData,
  });
}

export async function searchLocations(
  query: string,
  signal?: AbortSignal,
): Promise<LocationSearchResult[]> {
  const encodedQuery = encodeURIComponent(query.trim());

  try {
    return await request<LocationSearchResult[]>(
      `/geocode/search?query=${encodedQuery}`,
      { signal },
    );
  } catch (backendError) {
    // Keep search usable when the local FastAPI process cannot reach
    // Nominatim. The browser can often reach the public endpoint directly,
    // while the server may be behind a firewall or have no outbound network.
    if (signal?.aborted) throw backendError;

    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodedQuery}`,
        {
          signal,
          headers: { Accept: "application/json" },
          cache: "no-store",
        },
      );
      if (!response.ok) throw backendError;

      const payload = (await response.json()) as Array<{
        display_name?: unknown;
        lat?: unknown;
        lon?: unknown;
      }>;

      const results = payload.flatMap((item) => {
        const latitude = Number(item.lat);
        const longitude = Number(item.lon);
        if (
          typeof item.display_name !== "string" ||
          !Number.isFinite(latitude) ||
          !Number.isFinite(longitude)
        ) {
          return [];
        }
        return [{
          display_name: item.display_name,
          latitude,
          longitude,
        }];
      });

      if (results.length > 0) return results;
    } catch (directError) {
      if (signal?.aborted) throw directError;
    }

    throw backendError;
  }
}

export async function getComplaints(
  districtId?: number,
): Promise<Complaint[]> {
  const query = districtId ? `?district_id=${districtId}` : "";
  return request<Complaint[]>(`/complaints${query}`);
}

export async function getClusters(): Promise<LocationCluster[]> {
  return request<LocationCluster[]>("/clusters");
}

export async function getClusterDetail(
  clusterId: string,
): Promise<LocationClusterDetail> {
  return request<LocationClusterDetail>(
    `/clusters/${encodeURIComponent(clusterId)}`,
  );
}

export async function getTopUrgencyLocations(
  topN = 3,
): Promise<TopUrgencyLocation[]> {
  return request<TopUrgencyLocation[]>(
    `/insights/top-urgency-locations?top_n=${encodeURIComponent(topN)}`,
  );
}

export async function runSimulation(
  clusterIds: string[],
  totalBudget: number,
  equityContext?: Record<string, Record<string, unknown>>,
): Promise<Simulation> {
  return request<Simulation>("/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cluster_ids: clusterIds,
      total_budget: totalBudget,
      ...(equityContext ? { equity_context: equityContext } : {}),
    }),
  });
}

export async function getSimulation(id: number): Promise<Simulation> {
  return request<Simulation>(`/simulate/${id}`);
}

export async function getSimulationHistory(
  limit = 20,
): Promise<SimulationHistoryItem[]> {
  return request<SimulationHistoryItem[]>(`/simulate?limit=${encodeURIComponent(limit)}`);
}
