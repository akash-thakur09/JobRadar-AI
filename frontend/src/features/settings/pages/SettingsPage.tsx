import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { CareerSourcesCard } from "@/features/settings/components/CareerSourcesCard";
import { apiClient, apiGet, isApiBasePath, saveBrowserApiBase } from "@/lib/api-client";
import { extractErrorMessage } from "@/lib/utils";
import { settingsService, type RuntimeSettings, type RuntimeUpdate } from "@/services/settings.service";
import type { LivenessResponse } from "@/types/health";

const settingsKey = ["settings", "runtime"] as const;

function ApiConnectionCard() {
  const current = apiClient.defaults.baseURL || "/api/v1";
  const [path, setPath] = useState(current);
  const check = useMutation({
    mutationFn: async (save: boolean) => {
      const value = path.trim();
      if (value !== current && !isApiBasePath(value)) {
        throw new Error("Enter a same-origin path such as /api/v1.");
      }
      const result = await apiGet<LivenessResponse>("/health/live", { baseURL: value });
      if (result?.status !== "healthy" || typeof result.version !== "string") {
        throw new Error("This path did not return a JobRadar API health response.");
      }
      if (save && value !== current) {
        saveBrowserApiBase(value);
        window.location.reload();
      }
      return result;
    },
  });

  return (
    <Card>
      <CardHeader><CardTitle>Backend connection</CardTitle></CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={(event) => { event.preventDefault(); check.mutate(true); }}>
          <Input label="API proxy path" value={path} onChange={(event) => { setPath(event.target.value); check.reset(); }}
            helperText="This browser uses the path you save after verifying the backend responds."
            placeholder="/api/v1" required />
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" disabled={check.isPending} onClick={() => check.mutate(false)}>
              Test connection
            </Button>
            <Button type="submit" disabled={check.isPending || path.trim() === current}>Save API path</Button>
          </div>
          {check.error && <Alert variant="error">{extractErrorMessage(check.error, "API connection failed.")}</Alert>}
          {check.data && <p role="status" className="text-sm">Connected to JobRadar AI {check.data.version}.</p>}
        </form>
      </CardContent>
    </Card>
  );
}

function ConnectionTest({ service, label }: { service: "ollama" | "smtp"; label: string }) {
  const check = useMutation({ mutationFn: () => settingsService.test(service) });
  return (
    <div className="space-y-2">
      <Button type="button" variant="outline" isLoading={check.isPending} onClick={() => check.mutate()}>
        {label}
      </Button>
      {check.data && <Alert variant={check.data.ok ? "success" : "error"}>{check.data.message}</Alert>}
      {check.error && <Alert variant="error">{extractErrorMessage(check.error, "Connection check failed.")}</Alert>}
    </div>
  );
}

function RuntimeSettingsForm({ settings }: { settings: RuntimeSettings }) {
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: settingsService.update,
    onSuccess: (updated) => {
      queryClient.setQueryData(settingsKey, updated);
      void queryClient.invalidateQueries({ queryKey: ["health"] });
    },
  });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const password = String(values.get("smtp_password"));
    const payload: RuntimeUpdate = {
      ollama_model: String(values.get("ollama_model")).trim(),
      llm_timeout_seconds: Number(values.get("llm_timeout_seconds")),
      pipeline_scheduler_enabled: values.has("pipeline_scheduler_enabled"),
      pipeline_discovery_interval_hours: Number(values.get("pipeline_discovery_interval_hours")),
      email_provider: values.get("email_provider") === "mock" ? "mock" : "smtp",
      smtp_host: String(values.get("smtp_host")).trim(),
      smtp_port: Number(values.get("smtp_port")),
      smtp_username: String(values.get("smtp_username")).trim(),
      smtp_from_email: String(values.get("smtp_from_email")).trim(),
      smtp_use_tls: values.has("smtp_use_tls"),
      notification_recipient_email: String(values.get("notification_recipient_email")).trim(),
    };
    if (values.has("clear_smtp_password")) payload.smtp_password = "";
    else if (password) payload.smtp_password = password;
    try {
      await save.mutateAsync(payload);
      const passwordInput = form.elements.namedItem("smtp_password");
      if (passwordInput instanceof HTMLInputElement) passwordInput.value = "";
      const clearInput = form.elements.namedItem("clear_smtp_password");
      if (clearInput instanceof HTMLInputElement) clearInput.checked = false;
    } catch {
      // Display the save error below.
    }
  }

  const lockState = settings.scheduler_lock_held === null
    ? "Unavailable"
    : settings.scheduler_lock_held ? "Held during a scheduling check" : "Idle";

  return (
    <form className="space-y-4" onSubmit={submit} onChange={() => { if (save.isSuccess) save.reset(); }}>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Ollama</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="break-all text-sm text-terminal-muted">
              Provider {settings.llm_provider} · {settings.ollama_base_url}
            </p>
            <Input name="ollama_model" label="Model name" defaultValue={settings.ollama_model} maxLength={200} required />
            <Input name="llm_timeout_seconds" label="Request timeout (seconds)" type="number" min={1} max={180}
              step="0.1" defaultValue={settings.llm_timeout_seconds} required />
            <ConnectionTest service="ollama" label="Test saved Ollama connection" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Pipeline scheduler</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-2 text-sm">
              <input name="pipeline_scheduler_enabled" type="checkbox" defaultChecked={settings.pipeline_scheduler_enabled} />
              Enable scheduled pipeline runs
            </label>
            <Input name="pipeline_discovery_interval_hours" label="Minimum time between runs (hours)"
              type="number" min={1} max={720} defaultValue={settings.pipeline_discovery_interval_hours} required />
            <p className="text-sm text-terminal-muted">Standalone scheduler lock · {lockState}</p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader><CardTitle>Email notifications</CardTitle></CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="block space-y-1 text-sm">
            <span className="font-medium">Provider</span>
            <select name="email_provider" defaultValue={settings.email_provider}
              className="block w-full rounded-card border border-terminal-warmBorder bg-terminal-warmSurface p-2">
              <option value="smtp">SMTP</option>
              <option value="mock">Mock</option>
            </select>
          </label>
          <Input name="notification_recipient_email" label="Notification recipient" type="email" maxLength={255}
            defaultValue={settings.notification_recipient_email} placeholder="you@example.com" />
          <Input name="smtp_from_email" label="Sender email" type="email" maxLength={255}
            defaultValue={settings.smtp_from_email} required />
          <Input name="smtp_host" label="SMTP host" defaultValue={settings.smtp_host} maxLength={253} required />
          <Input name="smtp_port" label="SMTP port" type="number" min={1} max={65535} defaultValue={settings.smtp_port} required />
          <Input name="smtp_username" label="SMTP username" defaultValue={settings.smtp_username}
            maxLength={255} autoComplete="off" />
          <Input name="smtp_password" label="SMTP password" type="password" autoComplete="new-password" maxLength={1024}
            helperText={settings.smtp_password_configured ? "A password is saved. Enter a new one to replace it." : "Enter a password if the relay requires authentication."} />
          <div className="space-y-2 pt-1 text-sm">
            <label className="flex items-center gap-2">
              <input name="smtp_use_tls" type="checkbox" defaultChecked={settings.smtp_use_tls} />
              Use STARTTLS
            </label>
            <label className="flex items-center gap-2">
              <input name="clear_smtp_password" type="checkbox" disabled={!settings.smtp_password_configured} />
              Clear saved password
            </label>
          </div>
          <ConnectionTest service="smtp" label="Test saved email connection" />
        </CardContent>
      </Card>
      {save.error && <Alert variant="error">{extractErrorMessage(save.error, "Unable to save settings.")}</Alert>}
      {save.isSuccess && <Alert variant="success">Settings saved.</Alert>}
      <Button type="submit" isLoading={save.isPending}>Save settings</Button>
    </form>
  );
}

export function SettingsPage() {
  const settings = useQuery({ queryKey: settingsKey, queryFn: settingsService.get, refetchInterval: 15000 });

  return (
    <div className="space-y-5">
      <PageHeader title="Settings & Configuration" breadcrumbs={[{ label: "Settings & Configuration" }]} />
      <ApiConnectionCard />
      {settings.isLoading && <LoadingState message="Loading settings…" />}
      {settings.isError && <ErrorState title="Could not load settings" message="Check the backend connection and try again."
        onRetry={() => settings.refetch()} />}
      {settings.data && (
        <>
          <RuntimeSettingsForm settings={settings.data} />
          <CareerSourcesCard hosts={settings.data.career_page_allowed_hosts} />
        </>
      )}
    </div>
  );
}
