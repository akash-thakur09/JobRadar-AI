import { Link } from "react-router-dom";
import { ArrowRight, Globe, MapPin, ExternalLink, FolderOpen } from "lucide-react";
import { useJobs } from "@/hooks/useJobs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";

export function RecentJobsCard() {
  const { data: jobsResponse, isLoading, error } = useJobs({ page_size: 5 });

  const jobs = jobsResponse?.items || [];
  const totalCount = jobsResponse?.pagination?.total_items || 0;

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-terminal-primary" />
            <span>Recent Job Discoveries</span>
          </CardTitle>
          <CardDescription>
            {totalCount > 0
              ? `${totalCount} canonical opportunities discovered from configured boards`
              : "Upstream crawler discoveries"}
          </CardDescription>
        </div>
        <Link
          to="/discovery"
          className="text-xs font-mono font-medium text-terminal-primary hover:text-terminal-primaryHover flex items-center gap-1 shrink-0 pt-0.5"
        >
          <span>View All</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-between">
        {isLoading ? (
          <div className="py-12 flex justify-center items-center">
            <Spinner size="md" label="Loading discovered jobs..." />
          </div>
        ) : error ? (
          <div className="p-4 rounded-card bg-terminal-error/10 border border-terminal-error/30 text-terminal-errorText text-xs font-mono text-center">
            Unable to fetch discovered jobs. Please verify server connectivity.
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-8 rounded-card border-2 border-dashed border-terminal-warmBorder bg-terminal-warm/20 p-5">
            <FolderOpen className="w-6 h-6 text-terminal-muted mx-auto mb-2" />
            <p className="text-xs font-medium text-terminal-dark font-display">No jobs discovered yet</p>
            <p className="text-[11px] text-terminal-muted mt-0.5 max-w-xs mx-auto">
              Execute a pipeline run to crawl upstream career endpoints and ingest postings.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-terminal-warmBorder/60">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="py-3 first:pt-0 last:pb-0 flex items-start justify-between gap-3 group"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-xs font-semibold font-display text-terminal-dark truncate group-hover:text-terminal-primary transition-colors">
                      {job.title}
                    </h4>
                    <Badge
                      variant={
                        job.workplace_type === "REMOTE"
                          ? "lime"
                          : job.workplace_type === "HYBRID"
                          ? "ai"
                          : "neutral"
                      }
                      className="text-[10px] py-0 px-1.5"
                    >
                      {job.workplace_type}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-2 text-[11px] text-terminal-muted mt-1 font-sans flex-wrap">
                    <span className="font-medium text-terminal-dark">{job.canonical_company_name}</span>
                    <span>&bull;</span>
                    <span className="flex items-center gap-0.5">
                      <MapPin className="w-3 h-3 text-terminal-muted" />
                      <span className="truncate max-w-[120px]">{job.normalized_location || "Remote"}</span>
                    </span>
                    <span>&bull;</span>
                    <span className="font-mono text-[10px]">
                      {formatDate(job.posted_at || job.first_seen_at)}
                    </span>
                  </div>
                </div>

                {job.canonical_application_url && (
                  <a
                    href={job.canonical_application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 rounded-card text-terminal-muted hover:text-terminal-primary hover:bg-terminal-warm transition-colors shrink-0"
                    title="Open original job posting"
                    aria-label={`Open posting for ${job.title} at ${job.canonical_company_name}`}
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="pt-3 mt-3 border-t border-terminal-warmBorder flex items-center justify-between text-[11px] font-mono text-terminal-muted">
          <span>Source: Greenhouse, Lever, Direct</span>
          <Link to="/discovery" className="hover:text-terminal-dark transition-colors">
            Configure sources &rarr;
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

