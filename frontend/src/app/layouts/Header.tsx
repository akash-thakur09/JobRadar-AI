import { Menu, Play, RefreshCw, Server } from "lucide-react";
import { Link } from "react-router-dom";
import { useUIStore } from "@/stores/ui.store";
import { useSystemReadiness } from "@/hooks/useSystemHealth";
import { Button } from "@/components/ui/Button";

export function Header() {
  const { toggleMobileSidebar } = useUIStore();
  const { data: readiness, isLoading: isHealthLoading, refetch: refetchHealth } = useSystemReadiness();

  const isHealthy = readiness?.status === "healthy";

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 sm:px-6 bg-terminal-warmSurface/90 backdrop-blur-xs border-b border-terminal-warmBorder shadow-subtle">
      {/* Left: Mobile Toggle & Context */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleMobileSidebar}
          className="p-2 -ml-2 rounded-md text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm lg:hidden"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2">
          <span className="text-xs font-semibold text-terminal-muted uppercase font-mono tracking-wider">
            JobRadar AI Workspace
          </span>
        </div>
      </div>

      {/* Right: Operational Status & Fast Actions */}
      <div className="flex items-center gap-3">
        {/* Backend Readiness Indicator */}
        <div
          className="flex items-center gap-2 px-2.5 py-1 rounded-card text-xs font-mono border transition-colors bg-terminal-warm border-terminal-warmBorder"
          title={`PostgreSQL: ${readiness?.components.database || "Unknown"}, Redis: ${readiness?.components.redis || "Unknown"}, Ollama: ${readiness?.components.ollama || "Unknown"}`}
        >
          <Server className="w-3.5 h-3.5 text-terminal-muted shrink-0" />
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              isHealthLoading
                ? "bg-terminal-amber animate-ping"
                : isHealthy
                ? "bg-terminal-success"
                : "bg-terminal-error"
            }`}
          />
          <span className="hidden md:inline text-terminal-dark">
            {isHealthLoading
              ? "Checking..."
              : isHealthy
              ? "Backend Ready"
              : "Backend Issues"}
          </span>
          <button
            onClick={() => refetchHealth()}
            className="text-terminal-muted hover:text-terminal-dark ml-0.5"
            title="Refresh backend readiness check"
            aria-label="Refresh health"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>

        {/* Quick Trigger Action */}
        <Link to="/pipeline">
          <Button size="sm" variant="primary" className="gap-1.5 shadow-subtle">
            <Play className="w-3.5 h-3.5 fill-current" />
            <span className="hidden sm:inline">Pipeline Runs</span>
          </Button>
        </Link>
      </div>
    </header>
  );
}

