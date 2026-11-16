import { Link } from "react-router-dom";
import { Building2, MapPin, ExternalLink, Calendar, ArrowRight } from "lucide-react";
import type { JobSummary } from "@/types/jobs";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";

export interface JobCardProps {
  job: JobSummary;
}

export function JobCard({ job }: JobCardProps) {
  const getWorkplaceBadgeVariant = (wp: string) => {
    switch (wp?.toUpperCase()) {
      case "REMOTE":
        return "success";
      case "HYBRID":
        return "warning";
      case "ONSITE":
        return "neutral";
      default:
        return "neutral";
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status?.toUpperCase()) {
      case "ACTIVE":
        return "success";
      case "DISCOVERED":
        return "brand";
      case "EXPIRED":
      case "ARCHIVED":
        return "danger";
      default:
        return "neutral";
    }
  };

  const displayDate = job.posted_at || job.first_seen_at || job.created_at;

  return (
    <Card className="hover:border-terminal-muted/60 transition-all shadow-subtle group">
      <CardContent className="p-5 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        {/* Left Column: Job Info */}
        <div className="space-y-2 flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={getStatusBadgeVariant(job.status)} className="text-[10px] uppercase font-mono py-0 px-2">
              {job.status}
            </Badge>

            {job.workplace_type && (
              <Badge variant={getWorkplaceBadgeVariant(job.workplace_type)} className="text-[10px] uppercase font-mono py-0 px-2">
                {job.workplace_type}
              </Badge>
            )}

            {job.employment_type && job.employment_type !== "UNKNOWN" && (
              <span className="text-[11px] font-mono text-terminal-muted bg-terminal-warm px-2 py-0.5 rounded border border-terminal-warmBorder">
                {job.employment_type.replace("_", " ")}
              </span>
            )}
          </div>

          <div>
            <h3 className="text-base sm:text-lg font-bold font-display text-terminal-dark group-hover:text-terminal-primary transition-colors leading-snug">
              <Link to={`/jobs/${job.id}`} className="hover:underline">
                {job.title}
              </Link>
            </h3>

            <div className="flex items-center gap-3 text-xs text-terminal-muted mt-1 font-sans flex-wrap">
              <span className="font-semibold text-terminal-dark flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-terminal-muted" />
                <span>{job.canonical_company_name}</span>
              </span>

              <span>&bull;</span>

              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-terminal-muted" />
                <span>{job.normalized_location || "Location not specified"}</span>
              </span>

              {displayDate && (
                <>
                  <span>&bull;</span>
                  <span className="flex items-center gap-1 font-mono text-[11px]">
                    <Calendar className="w-3 h-3 text-terminal-muted" />
                    <span>{formatDate(displayDate)}</span>
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Actions */}
        <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2.5 shrink-0 pt-1 border-t sm:border-t-0 border-terminal-warmBorder/60 sm:pt-0">
          <Link to={`/jobs/${job.id}`} className="w-full sm:w-auto">
            <Button variant="outline" size="sm" className="w-full text-xs gap-1.5 font-sans">
              <span>View Details</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>

          {job.canonical_application_url && (
            <a
              href={job.canonical_application_url}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto"
            >
              <Button
                variant="primary"
                size="sm"
                className="w-full text-xs gap-1.5 shadow-subtle font-sans"
              >
                <span>Apply</span>
                <ExternalLink className="w-3 h-3" />
              </Button>
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
