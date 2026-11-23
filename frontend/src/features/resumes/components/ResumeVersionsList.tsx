import { Layers, Clock } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import type { ResumeVersionResponse, ResumeVersionSummary } from "@/types/resumes";

interface ResumeVersionsListProps {
  versions: (ResumeVersionSummary | ResumeVersionResponse)[];
  currentVersionId?: string;
  onSelectVersion?: (versionId: string) => void;
}

export function ResumeVersionsList({
  versions,
  currentVersionId,
  onSelectVersion,
}: ResumeVersionsListProps) {
  if (!versions || versions.length === 0) {
    return (
      <div className="p-4 text-xs text-terminal-muted italic bg-terminal-warm rounded-card border border-terminal-warmBorder">
        No parsing versions recorded for this master resume.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {versions.map((ver) => {
        const isSelected = ver.id === currentVersionId;
        return (
          <div
            key={ver.id}
            onClick={() => onSelectVersion && onSelectVersion(ver.id)}
            className={`flex items-center justify-between p-3 rounded-card border transition-all ${
              onSelectVersion ? "cursor-pointer" : ""
            } ${
              isSelected
                ? "bg-terminal-warm border-terminal-primary shadow-xs"
                : "bg-terminal-warmSurface border-terminal-warmBorder hover:border-terminal-muted/60"
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-terminal-warm flex items-center justify-center text-terminal-muted border border-terminal-warmBorder">
                <Layers className="w-4 h-4 text-terminal-dark" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold font-mono text-terminal-dark">
                    Version {ver.version_number}
                  </span>
                  {isSelected && (
                    <Badge variant="lime" className="text-[10px] py-0">
                      Active Version
                    </Badge>
                  )}
                  {ver.is_valid ? (
                    <Badge variant="success" className="text-[10px] py-0">
                      Valid
                    </Badge>
                  ) : (
                    <Badge variant="danger" className="text-[10px] py-0">
                      Invalid
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-[11px] text-terminal-muted font-mono">
                  <Clock className="w-3 h-3" />
                  <span>{formatDate(ver.created_at)}</span>
                  {"checksum_sha256" in ver && (
                    <span className="truncate max-w-[140px]" title={ver.checksum_sha256}>
                      &bull; SHA: {ver.checksum_sha256.substring(0, 8)}...
                    </span>
                  )}
                </div>
              </div>
            </div>

            <Badge
              variant={ver.processing_status === "COMPLETED" ? "success" : ver.processing_status === "FAILED" ? "danger" : "warning"}
              withDot
              className="text-[11px]"
            >
              {ver.processing_status}
            </Badge>
          </div>
        );
      })}
    </div>
  );
}
