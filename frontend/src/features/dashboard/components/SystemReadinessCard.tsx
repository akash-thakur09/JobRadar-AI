import { Server, Database, Cpu, HardDrive } from "lucide-react";
import type { ReadinessResponse, LivenessResponse } from "@/types/health";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export interface SystemReadinessCardProps {
  readiness: ReadinessResponse | undefined;
  liveness: LivenessResponse | undefined;
  isLoading?: boolean;
}

function ComponentStatus({ detail, checking }: { detail?: string; checking?: boolean }) {
  const variant = detail === "healthy" ? "success" : detail ? "warning" : "neutral";
  return <Badge variant={variant}>{detail || (checking ? "Checking" : "Unavailable")}</Badge>;
}

export function SystemReadinessCard({ readiness, liveness, isLoading }: SystemReadinessCardProps) {
  const isHealthy = readiness?.status === "healthy";

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Server className="w-4 h-4 text-terminal-primary" />
            <span>Infrastructure Health</span>
          </CardTitle>
          <CardDescription>Live backend services and AI engine status</CardDescription>
        </div>
        <Badge variant={isHealthy ? "success" : "danger"} withDot>
          {isLoading ? "Checking" : isHealthy ? "Platform Healthy" : "Degraded"}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-3.5 flex-1">
        {/* Core Services */}
        <div className="space-y-2 text-xs">
          {/* Database */}
          <div className="flex items-center justify-between p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/80">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-terminal-muted" />
              <span className="font-semibold font-display text-terminal-dark">PostgreSQL 16</span>
            </div>
            <ComponentStatus detail={readiness?.components.database} checking={isLoading} />
          </div>

          {/* Redis */}
          <div className="flex items-center justify-between p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/80">
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-terminal-muted" />
              <span className="font-semibold font-display text-terminal-dark">Redis & Celery</span>
            </div>
            <ComponentStatus detail={readiness?.components.redis} checking={isLoading} />
          </div>

          {/* Ollama LLM */}
          <div className="flex items-center justify-between p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/80">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-terminal-muted" />
              <span className="font-semibold font-display text-terminal-dark">LLM provider</span>
            </div>
            <ComponentStatus detail={readiness?.components.ollama} checking={isLoading} />
          </div>
        </div>

        {/* Runtime info */}
        <div className="flex items-center justify-between text-[11px] font-mono text-terminal-muted pt-2 border-t border-terminal-warmBorder">
          <span>Environment <code className="text-terminal-dark">{liveness?.environment || "Unavailable"}</code></span>
          <span>Version <code className="text-terminal-dark">{liveness?.version ? `v${liveness.version}` : "Unavailable"}</code></span>
        </div>
      </CardContent>
    </Card>
  );
}

