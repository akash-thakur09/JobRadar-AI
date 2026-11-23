import { type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { extractErrorMessage } from "@/lib/utils";
import { settingsService, type CareerSource } from "@/services/settings.service";

const sourceKey = ["settings", "career-sources"] as const;

export function CareerSourcesCard({ hosts }: { hosts: string[] }) {
  const queryClient = useQueryClient();
  const sources = useQuery({
    queryKey: sourceKey,
    queryFn: settingsService.listCareerSources,
    refetchInterval: (query) =>
      query.state.data?.some((source) => ["PENDING", "RUNNING"].includes(source.latest_run?.status ?? ""))
        ? 2000
        : false,
  });
  const add = useMutation({
    mutationFn: settingsService.addCareerSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sourceKey }),
  });
  const run = useMutation({
    mutationFn: settingsService.runCareerSource,
    onSuccess: (latest_run, id) => {
      queryClient.setQueryData<CareerSource[]>(sourceKey, (cached) =>
        cached?.map((source) => source.id === id ? { ...source, latest_run } : source),
      );
      return queryClient.invalidateQueries({ queryKey: sourceKey });
    },
  });
  const enable = useMutation({
    mutationFn: ({ id, isEnabled }: { id: string; isEnabled: boolean }) =>
      settingsService.enableCareerSource(id, isEnabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sourceKey }),
  });

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    try {
      await add.mutateAsync({
        name: String(values.get("name")).trim(),
        base_url: String(values.get("url")).trim(),
        configuration: {
          permitted: true,
          job_link_prefix: String(values.get("prefix")).trim() || undefined,
        },
      });
      form.reset();
    } catch {
      // Display the mutation error with the form.
    }
  }

  const error = sources.error || add.error || run.error || enable.error;
  return (
    <Card>
      <CardHeader><CardTitle>Career page sources</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {error && <Alert variant="error">{extractErrorMessage(error, "Career page request failed.")}</Alert>}
        {hosts.length ? (
          <>
            <p className="text-sm text-terminal-muted">Approved hosts {hosts.join(", ")}</p>
            <form onSubmit={register} className="grid gap-4 sm:grid-cols-2">
              <Input name="name" label="Company or source name" maxLength={100} required />
              <Input name="url" label="Public career page URL" type="url" maxLength={512} required />
              <div className="sm:col-span-2">
                <Input name="prefix" label="Job link path (optional)" maxLength={512}
                  placeholder="/careers/jobs/"
                  helperText="Use a path for pages that list job links without structured job data." />
              </div>
              <label className="flex gap-2 text-sm sm:col-span-2">
                <input type="checkbox" name="permitted" required />
                This page permits automated access to its public listings.
              </label>
              <div><Button type="submit" isLoading={add.isPending}>Add source</Button></div>
            </form>
          </>
        ) : (
          <p className="text-sm text-terminal-muted">
            Set CAREER_PAGE_ALLOWED_HOSTS in the backend environment to register approved pages.
          </p>
        )}
        {sources.data?.map((source) => {
          const busy = ["PENDING", "RUNNING"].includes(source.latest_run?.status ?? "");
          return (
            <div key={source.id} className="flex flex-wrap justify-between gap-3 border-t border-terminal-warmBorder pt-3">
              <div className="min-w-0">
                <p className="font-medium">{source.name}</p>
                <p className="break-all text-xs text-terminal-muted">{source.base_url}</p>
                {source.latest_run && (
                  <>
                    <p className="text-sm" role="status">
                      {source.latest_run.status} · {source.latest_run.jobs_discovered} discovered
                    </p>
                    {source.latest_run.error_summary && (
                      <p className="text-xs text-terminal-muted">{source.latest_run.error_summary}</p>
                    )}
                  </>
                )}
              </div>
              <div className="flex gap-2">
                <Button type="button" size="sm" variant="outline" disabled={enable.isPending}
                  onClick={() => enable.mutate({ id: source.id, isEnabled: !source.is_enabled })}>
                  {source.is_enabled ? "Disable" : "Enable"}
                </Button>
                <Button type="button" size="sm" disabled={!source.is_enabled || busy || run.isPending}
                  onClick={() => run.mutate(source.id)}>Run discovery</Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
