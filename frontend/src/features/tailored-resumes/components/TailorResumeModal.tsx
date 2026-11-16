import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  X,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { useResumes } from "@/hooks/useResumes";
import { useCreateTailoredResume } from "@/hooks/useTailoredResumes";
import { useReevaluateMatch } from "@/hooks/useMatches";
import { extractErrorMessage } from "@/lib/utils";

interface TailorResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  jobTitle?: string;
  companyName?: string;
  jobMatchId?: string;
  isQualified?: boolean;
}

export function TailorResumeModal({
  isOpen,
  onClose,
  jobId,
  jobTitle,
  companyName,
  jobMatchId: initialJobMatchId,
  isQualified: initialIsQualified,
}: TailorResumeModalProps) {
  const navigate = useNavigate();

  const [currentJobMatchId, setCurrentJobMatchId] = useState<string | undefined>(initialJobMatchId);
  const [currentIsQualified, setCurrentIsQualified] = useState<boolean | undefined>(initialIsQualified);
  const [selectedResumeId, setSelectedResumeId] = useState<string>("");
  const [forceRegenerate, setForceRegenerate] = useState(false);

  const { data: resumesResponse, isLoading: isLoadingResumes } = useResumes();
  const tailorMutation = useCreateTailoredResume();
  const reevaluateMutation = useReevaluateMatch();

  const resumes = useMemo(() => resumesResponse?.items || [], [resumesResponse]);
  const activeResume = useMemo(() => resumes.find((r) => r.is_active), [resumes]);

  // Sync initial props
  useEffect(() => {
    setCurrentJobMatchId(initialJobMatchId);
    setCurrentIsQualified(initialIsQualified);
  }, [initialJobMatchId, initialIsQualified]);

  // Set default selected resume when resumes load
  useEffect(() => {
    if (activeResume && !selectedResumeId) {
      setSelectedResumeId(activeResume.id);
    } else if (resumes.length > 0 && !selectedResumeId && resumes[0]) {
      setSelectedResumeId(resumes[0].id);
    }
  }, [activeResume, resumes, selectedResumeId]);

  if (!isOpen) return null;

  const handleEvaluateMatch = async () => {
    try {
      const matchResult = await reevaluateMutation.mutateAsync({ jobId });
      setCurrentJobMatchId(matchResult.id);
      setCurrentIsQualified(matchResult.is_qualified);
    } catch {
      // Handled by react query mutation state
    }
  };

  const handleSubmit = async () => {
    if (!currentJobMatchId) return;

    try {
      const chosenResume = resumes.find((r) => r.id === selectedResumeId);
      const resumeVersionId = chosenResume?.latest_version?.id || null;

      const result = await tailorMutation.mutateAsync({
        job_match_id: currentJobMatchId,
        resume_version_id: resumeVersionId,
        force_regenerate: forceRegenerate,
      });

      onClose();
      navigate(`/tailored-resumes/${result.id}`);
    } catch {
      // Handled by react query mutation state
    }
  };

  const canTailor = Boolean(currentJobMatchId && currentIsQualified === true);
  const isMatchEvaluated = currentJobMatchId !== undefined;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-terminal-dark/70 backdrop-blur-xs p-4">
      <div
        className="w-full max-w-lg bg-terminal-warmSurface border border-terminal-warmBorder rounded-card shadow-2xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tailor-modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-terminal-warmBorder">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-card bg-terminal-primary/10 text-terminal-primary flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 id="tailor-modal-title" className="text-base font-bold font-display text-terminal-dark">
                Tailor Resume for Position
              </h2>
              <p className="text-xs text-terminal-muted truncate max-w-sm mt-0.5">
                {jobTitle || "Target Position"} &bull; {companyName || "Target Company"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Match Eligibility Status Check */}
          {!isMatchEvaluated ? (
            <div className="p-4 bg-terminal-warm rounded-card border border-terminal-warmBorder space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-terminal-dark">
                <AlertTriangle className="w-4 h-4 text-terminal-warning" />
                Match Evaluation Required
              </div>
              <p className="text-xs text-terminal-muted leading-relaxed">
                Before generating a truthful tailored resume, JobRadar AI must run deterministic match qualification against your profile criteria.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleEvaluateMatch}
                isLoading={reevaluateMutation.isPending}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Evaluate Match Now
              </Button>
            </div>
          ) : currentIsQualified === false ? (
            <Alert variant="error" title="Ineligible for Resume Tailoring">
              <div className="space-y-1 mt-1 text-xs">
                <p>
                  The deterministic matching engine evaluated this position as <strong>not qualified</strong> based on hard constraints (e.g. required skills, minimum experience, or workplace preference).
                </p>
                <p className="text-terminal-muted pt-1">
                  JobRadar AI strictly enforces zero hallucination and will not generate tailored resumes for disqualified positions.
                </p>
              </div>
            </Alert>
          ) : (
            <div className="p-3 bg-terminal-success/10 border border-terminal-success/30 rounded-card flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-terminal-success shrink-0" />
                <span className="text-xs font-semibold text-[#185C36]">
                  Candidate Profile Qualified for Tailoring
                </span>
              </div>
              <Badge variant="success" className="text-[10px]">
                Eligible
              </Badge>
            </div>
          )}

          {/* Master Resume Source Selector */}
          <div className="space-y-2">
            <label className="text-xs font-bold font-display text-terminal-dark flex items-center justify-between">
              <span>Source Master Resume</span>
              {activeResume && (
                <span className="text-[10px] text-terminal-muted font-normal">
                  Active: {activeResume.original_filename}
                </span>
              )}
            </label>

            {isLoadingResumes ? (
              <div className="text-xs text-terminal-muted font-mono p-2">Loading resumes...</div>
            ) : resumes.length === 0 ? (
              <div className="p-3 bg-terminal-warning/10 border border-terminal-warning/30 rounded-card text-xs text-[#6E4C00]">
                No master resumes found. Please upload a resume first.
              </div>
            ) : (
              <select
                value={selectedResumeId}
                onChange={(e) => setSelectedResumeId(e.target.value)}
                className="w-full h-9 px-3 text-xs bg-terminal-warmSurface border border-terminal-warmBorder rounded-card font-mono text-terminal-dark focus:outline-none focus:ring-1 focus:ring-terminal-primary"
              >
                {resumes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.original_filename} {r.is_active ? "(Active Master)" : ""} &mdash; v{r.latest_version?.version_number || 1}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Force Regenerate Checkbox */}
          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="forceRegenerate"
              checked={forceRegenerate}
              onChange={(e) => setForceRegenerate(e.target.checked)}
              className="rounded border-terminal-warmBorder text-terminal-primary focus:ring-terminal-primary"
            />
            <label htmlFor="forceRegenerate" className="text-xs text-terminal-dark cursor-pointer select-none">
              Force re-generation if a tailored resume already exists for this match
            </label>
          </div>

          {/* Pipeline Details info */}
          <div className="p-3 bg-terminal-warm/60 rounded-card border border-terminal-warmBorder text-[11px] text-terminal-muted space-y-1">
            <p className="font-semibold text-terminal-dark">Truthful Tailoring Guarantees:</p>
            <ul className="list-disc list-inside space-y-0.5">
              <li>ATS-optimized single-column typesetting with template preservation</li>
              <li>LLM claim validation ensures zero hallucinated skills or metrics</li>
              <li>Generates audit report of all supported and filtered claims</li>
            </ul>
          </div>

          {/* Error Alert */}
          {tailorMutation.isError && (
            <Alert variant="error" title="Tailoring Request Failed">
              {extractErrorMessage(tailorMutation.error, "Failed to enqueue tailored resume generation.")}
            </Alert>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 bg-terminal-warm/50 border-t border-terminal-warmBorder">
          <Button variant="outline" size="sm" onClick={onClose} disabled={tailorMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!canTailor || tailorMutation.isPending || !selectedResumeId}
            isLoading={tailorMutation.isPending}
            onClick={handleSubmit}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Generate Tailored Resume
          </Button>
        </div>
      </div>
    </div>
  );
}
