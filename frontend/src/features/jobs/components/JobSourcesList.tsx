import { Globe, Hash, Clock, ExternalLink } from "lucide-react";
import type { JobSourceRecord } from "@/types/jobs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";

export interface JobSourcesListProps {
  sources: JobSourceRecord[];
  dedupFingerprint?: string;
}

export function JobSourcesList({ sources, dedupFingerprint }: JobSourcesListProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <Globe className="w-4 h-4 text-terminal-primary" />
            <span>Discovery Provenance & Ingestion Audit</span>
          </CardTitle>
          <Badge variant="brand" className="text-[10px] font-mono">
            {sources.length} {sources.length === 1 ? "Source" : "Sources"} Linked
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Cross-source deduplication audit records tracking raw ATS postings
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {dedupFingerprint && (
          <div className="p-3 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder text-xs space-y-1">
            <div className="flex items-center gap-1.5 text-terminal-muted font-mono text-[11px]">
              <Hash className="w-3.5 h-3.5 text-terminal-muted" />
              <span className="font-semibold uppercase text-terminal-dark">Deduplication Fingerprint (SHA-256):</span>
            </div>
            <p className="font-mono text-[11px] text-terminal-dark break-all bg-white px-2 py-1 rounded border border-terminal-warmBorder">
              {dedupFingerprint}
            </p>
          </div>
        )}

        {sources.length === 0 ? (
          <p className="text-xs text-terminal-muted italic font-mono py-2">
            No external source records linked directly. Canonical record initialized via ingest pipeline.
          </p>
        ) : (
          <div className="divide-y divide-terminal-warmBorder/60 border border-terminal-warmBorder rounded-card overflow-hidden">
            {sources.map((src) => (
              <div key={src.id} className="p-3.5 bg-terminal-warmSurface space-y-2 text-xs">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="neutral" className="font-mono text-[10px]">
                      {src.processing_status}
                    </Badge>
                    <span className="font-mono text-[11px] text-terminal-muted">
                      Ext ID: <span className="text-terminal-dark font-medium">{src.external_job_id}</span>
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-[11px] text-terminal-muted font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>First Seen: {formatDate(src.first_seen_at)}</span>
                    </span>
                  </div>
                </div>

                {src.source_job_url && (
                  <div className="flex items-center gap-1 text-[11px] text-terminal-muted">
                    <span className="shrink-0 font-medium">Source URL:</span>
                    <a
                      href={src.source_job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-terminal-primary hover:underline truncate inline-flex items-center gap-1"
                    >
                      <span className="truncate">{src.source_job_url}</span>
                      <ExternalLink className="w-3 h-3 shrink-0" />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

