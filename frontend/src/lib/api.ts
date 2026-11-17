const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("haki_token") : null;

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (organisation_name: string, full_name: string, email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ organisation_name, full_name, email, password }),
    }),
  me: () => request<{ id: string; email: string; full_name: string; role: string }>("/api/auth/me"),
  leads: () => request<Lead[]>("/api/leads"),
  lead: (id: string) => request<Lead>(`/api/leads/${id}`),
  companyProfile: () => request<Record<string, unknown>>("/api/company-profile"),

  researchLead: (id: string) =>
    request<Record<string, unknown>>(`/api/leads/${id}/research`, { method: "POST" }),
  qualifyLead: (id: string) =>
    request<{ score: number; classification: string; explanation: string }>(
      `/api/leads/${id}/qualify`,
      { method: "POST" }
    ),

  startDiscovery: (params: DiscoveryStartParams) =>
    request<DiscoveryJob>("/api/discovery/start", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  discoveryJobs: () => request<DiscoveryJob[]>("/api/discovery/jobs"),
  discoveryJob: (id: string) => request<DiscoveryJob>(`/api/discovery/jobs/${id}`),
  pauseDiscovery: (id: string) =>
    request<DiscoveryJob>(`/api/discovery/jobs/${id}/pause`, { method: "POST" }),
  resumeDiscovery: (id: string) =>
    request<DiscoveryJob>(`/api/discovery/jobs/${id}/resume`, { method: "POST" }),
  cancelDiscovery: (id: string) =>
    request<DiscoveryJob>(`/api/discovery/jobs/${id}/cancel`, { method: "POST" }),
};

export type Lead = {
  id: string;
  business_name: string;
  website: string;
  country: string | null;
  city: string | null;
  industry: string | null;
  business_email: string | null;
  phone_number: string | null;
  contact_person: string | null;
  identified_opportunity: string | null;
  recommended_service: string | null;
  status: string;
  is_unsubscribed: boolean;
  created_at: string;
};

export type DiscoveryStartParams = {
  country?: string;
  city?: string;
  industry?: string;
  business_type?: string;
  keywords?: string;
  services?: string;
  num_leads?: number;
};

export type DiscoveryJob = {
  id: string;
  status: "pending" | "running" | "paused" | "completed" | "failed" | "cancelled";
  search_params: Record<string, unknown>;
  discovered_count: number;
  researched_count: number;
  failed_count: number;
  duplicate_count: number;
  qualified_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};
