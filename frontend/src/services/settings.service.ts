import { apiClient, apiGet, apiPost } from "@/lib/api-client";

export interface RuntimeSettings {
  ollama_model: string;
  ollama_base_url: string;
  llm_provider: string;
  llm_timeout_seconds: number;
  pipeline_scheduler_enabled: boolean;
  pipeline_discovery_interval_hours: number;
  scheduler_lock_held: boolean | null;
  email_provider: "smtp" | "mock";
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_from_email: string;
  smtp_use_tls: boolean;
  smtp_password_configured: boolean;
  notification_recipient_email: string;
  career_page_allowed_hosts: string[];
}

export type RuntimeUpdate = Omit<
  RuntimeSettings,
  "ollama_base_url" | "llm_provider" | "scheduler_lock_held" | "smtp_password_configured" | "career_page_allowed_hosts"
> & { smtp_password?: string };

export interface DiscoveryRun {
  id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "PARTIAL";
  jobs_discovered: number;
  error_summary?: string | null;
}

export interface CareerSource {
  id: string;
  name: string;
  base_url: string;
  source_type: string;
  is_enabled: boolean;
  latest_run?: DiscoveryRun | null;
}

export const settingsService = {
  get: () => apiGet<RuntimeSettings>("/settings"),
  update: async (payload: RuntimeUpdate) =>
    (await apiClient.patch<RuntimeSettings>("/settings", payload)).data,
  test: (service: "ollama" | "smtp") =>
    apiPost<{ ok: boolean; message: string }>(`/settings/test/${service}`),
  listCareerSources: async () => {
    const sources = await apiGet<CareerSource[]>("/discovery/sources");
    return sources.filter((source) => source.source_type === "CAREER_PAGE");
  },
  addCareerSource: (payload: {
    name: string;
    base_url: string;
    configuration: { permitted: true; job_link_prefix?: string };
  }) => apiPost<CareerSource>("/discovery/sources", { ...payload, source_type: "CAREER_PAGE" }),
  runCareerSource: (id: string) => apiPost<DiscoveryRun>(`/discovery/sources/${id}/discover`),
  enableCareerSource: async (id: string, isEnabled: boolean) =>
    (await apiClient.patch<CareerSource>(`/discovery/sources/${id}`, { is_enabled: isEnabled })).data,
};
