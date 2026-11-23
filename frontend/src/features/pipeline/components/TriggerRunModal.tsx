import { useState } from "react";
import { X, Play, Info } from "lucide-react";
import { useStartPipelineRun } from "@/hooks/usePipelineRuns";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { extractErrorMessage } from "@/lib/utils";
import type { PipelineTriggerType } from "@/types/pipeline";

export interface TriggerRunModalProps {
  candidateProfileId: string;
  onClose: () => void;
  onSuccess: (runId: string) => void;
}

export function TriggerRunModal({
  candidateProfileId,
  onClose,
  onSuccess,
}: TriggerRunModalProps) {
  const [triggerType, setTriggerType] = useState<PipelineTriggerType>("MANUAL");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const startMutation = useStartPipelineRun();

  const handleTrigger = async () => {
    setErrorMsg(null);
    try {
      const result = await startMutation.mutateAsync({
        candidate_profile_id: candidateProfileId,
        trigger_type: triggerType,
        metadata: {
          client: "JobRadar AI Web Console",
          triggered_by: "User manual request",
        },
      });
      onSuccess(result.id);
    } catch (err) {
      setErrorMsg(
        extractErrorMessage(
          err,
          "Failed to start pipeline run. If an active run is already running, please wait for it to complete."
        )
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-terminal-dark/70 backdrop-blur-xs">
      <div className="bg-terminal-warmSurface rounded-card shadow-dropdown border border-terminal-warmBorder max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-terminal-warmBorder">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-card bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-primary shadow-subtle">
              <Play className="w-4 h-4 fill-current" />
            </div>
            <div>
              <h3 className="text-sm font-bold font-display text-terminal-dark">Start Pipeline Run</h3>
              <p className="text-xs text-terminal-muted">Trigger full orchestration workflow</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {errorMsg && (
            <Alert variant="error" title="Cannot Start Run">
              {errorMsg}
            </Alert>
          )}

          <div className="p-3.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder text-xs text-terminal-dark space-y-2">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-terminal-primary shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold font-display text-terminal-dark">Orchestrated Lifecycle: </span>
                <span className="text-terminal-dark/90 font-sans">
                  The pipeline coordinates Job Discovery &rarr; Canonicalization &rarr;
                  Deterministic Matching &rarr; LLM Semantic Analysis &rarr; Truthful Resume Tailoring &rarr; Email Notification.
                </span>
              </div>
            </div>
            <p className="text-[11px] text-terminal-muted font-mono pl-6">
              Guarded by PostgreSQL partial unique index ensuring only 1 active run per candidate profile.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold font-display text-terminal-dark mb-1.5">
              Trigger Origin
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setTriggerType("MANUAL")}
                className={`px-3 py-2 rounded-card border text-xs font-medium text-center transition-colors font-mono ${
                  triggerType === "MANUAL"
                    ? "border-terminal-primary bg-terminal-primary/10 text-terminal-primary font-semibold"
                    : "border-terminal-warmBorder bg-terminal-warmSurface text-terminal-dark hover:bg-terminal-warm"
                }`}
              >
                Manual Trigger
              </button>
              <button
                type="button"
                onClick={() => setTriggerType("API")}
                className={`px-3 py-2 rounded-card border text-xs font-medium text-center transition-colors font-mono ${
                  triggerType === "API"
                    ? "border-terminal-primary bg-terminal-primary/10 text-terminal-primary font-semibold"
                    : "border-terminal-warmBorder bg-terminal-warmSurface text-terminal-dark hover:bg-terminal-warm"
                }`}
              >
                API Emulation
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-terminal-warmBorder bg-terminal-warm rounded-b-card flex items-center justify-end gap-2.5">
          <Button variant="outline" size="sm" onClick={onClose} disabled={startMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleTrigger}
            isLoading={startMutation.isPending}
            className="gap-1.5 shadow-subtle"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Enqueue Run</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
