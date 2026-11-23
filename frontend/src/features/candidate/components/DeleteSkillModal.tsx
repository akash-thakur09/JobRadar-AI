import { useState } from "react";
import { Trash2, X, AlertTriangle } from "lucide-react";
import type { CandidateSkill } from "@/types/candidate";
import { useDeleteCandidateSkill } from "@/hooks/useCandidateProfile";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { extractErrorMessage, formatExperience } from "@/lib/utils";

export interface DeleteSkillModalProps {
  skill: CandidateSkill;
  onClose: () => void;
  onSuccess: () => void;
}

export function DeleteSkillModal({ skill, onClose, onSuccess }: DeleteSkillModalProps) {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const deleteMutation = useDeleteCandidateSkill();

  const handleDelete = async () => {
    setErrorMsg(null);
    try {
      await deleteMutation.mutateAsync(skill.id);
      onSuccess();
    } catch (err) {
      setErrorMsg(extractErrorMessage(err, "Failed to delete skill. Please try again."));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-terminal-dark/70 backdrop-blur-xs">
      <div className="bg-terminal-warmSurface rounded-card shadow-dropdown border border-terminal-warmBorder max-w-sm w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-terminal-warmBorder">
          <div className="flex items-center gap-2 text-terminal-error">
            <Trash2 className="w-4 h-4" />
            <h3 className="text-sm font-bold font-display text-terminal-dark">Remove Skill</h3>
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
        <div className="p-5 space-y-3">
          {errorMsg && (
            <Alert variant="error" title="Delete Failed">
              {errorMsg}
            </Alert>
          )}

          <div className="flex items-start gap-3 p-3 rounded-card bg-terminal-error/10 border border-terminal-error/30 text-xs text-terminal-errorText">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <p>
              Are you sure you want to remove <span className="font-bold font-mono text-terminal-dark">{skill.skill_name}</span> from your Evidence Vault?
            </p>
          </div>

          <div className="p-3 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder text-xs space-y-1 font-mono">
            <div className="flex justify-between">
              <span className="text-terminal-muted">Category:</span>
              <span className="text-terminal-dark font-medium capitalize">{skill.category}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-muted">Experience:</span>
              <span className="text-terminal-dark font-medium">{formatExperience(skill.experience_months)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-terminal-muted">Type:</span>
              <span className="text-terminal-dark font-medium">{skill.is_core ? "Core Competency" : "Technical Skill"}</span>
            </div>
          </div>

          <p className="text-[11px] text-terminal-muted leading-relaxed font-sans">
            Future job matches and resume tailoring runs will no longer recognize this verified skill.
          </p>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-terminal-warmBorder bg-terminal-warm rounded-b-card flex items-center justify-end gap-2.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={deleteMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={handleDelete}
            isLoading={deleteMutation.isPending}
            className="shadow-subtle"
          >
            Confirm Removal
          </Button>
        </div>
      </div>
    </div>
  );
}

