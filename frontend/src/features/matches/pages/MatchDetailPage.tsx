import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Building2,
  MapPin,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Briefcase,
  FileText,
  Sparkles,
} from "lucide-react";
import { useMatch, useReevaluateMatch, useTriggerSemanticAnalysis } from "@/hooks/useMatches";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";
import { EligibilityBadge } from "../components/EligibilityBadge";
import { MatchScoreBadge } from "../components/MatchScoreBadge";
import { DeterministicScoreBreakdown } from "../components/DeterministicScoreBreakdown";
import { SemanticAnalysisSection } from "../components/SemanticAnalysisSection";
import { TailorResumeModal } from "@/features/tailored-resumes/components/TailorResumeModal";

export function MatchDetailPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isTailorModalOpen, setIsTailorModalOpen] = useState(false);

  const { data: match, isLoading, error, refetch } = useMatch(matchId || "");
  const reevaluateMutation = useReevaluateMatch();
  const semanticMutation = useTriggerSemanticAnalysis();

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleReevaluate = async () => {
    if (!match?.job_id) return;
    try {
      await reevaluateMutation.mutateAsync({ jobId: match.job_id });
      showToast("Deterministic matching re-evaluated successfully!");
      refetch();
    } catch {
      // Handled by react query mutation state
    }
  };

  const handleTriggerSemantic = async () => {
    if (!match?.id) return;
    try {
      await semanticMutation.mutateAsync(match.id);
      showToast("Layer 3 LLM Semantic Analysis completed!");
      refetch();
    } catch {
      // Handled by react query mutation state
    }
  };

  if (isLoading) {
    return <LoadingState message="Loading match evaluation & explainability breakdown..." />;
  }

  if (error || !match) {
    return (
      <ErrorState
        title="Match Not Found"
        message="Could not retrieve the requested match evaluation. It may not exist or has been re-evaluated."
        onRetry={() => refetch()}
        action={
          <Link to="/matches">
            <Button variant="outline" size="sm">
              &larr; Back to Matches
            </Button>
          </Link>
        }
      />
    );
  }

  const finalScore = Number(match.final_score) || 0;
  const isEligible = match.eligibility_status === "ELIGIBLE";
  const isQualified = match.is_qualified || (isEligible && finalScore >= 50);

  const eligDetails = match.match_explanation_details?.eligibility;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-2 rounded-card bg-terminal-success text-[#185C36] text-xs font-semibold border border-terminal-success/40 shadow-dropdown animate-bounce">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Back button */}
      <div>
        <Link
          to="/matches"
          className="inline-flex items-center gap-1.5 text-xs font-mono font-medium text-terminal-muted hover:text-terminal-dark transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to All Evaluated Matches</span>
        </Link>
      </div>

      {/* 1. Overall Match Summary Card */}
      <Card className="border-terminal-warmBorder shadow-card">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
            {/* Left: Job & Status Information */}
            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <EligibilityBadge status={match.eligibility_status} />

                {isQualified ? (
                  <Badge variant="success" className="font-mono text-[10px] uppercase">
                    Qualified Opportunity
                  </Badge>
                ) : (
                  <Badge variant="neutral" className="font-mono text-[10px] uppercase">
                    Below Threshold
                  </Badge>
                )}

                {match.workplace_type && (
                  <span className="text-[10px] font-mono text-terminal-muted bg-terminal-warm px-2 py-0.5 rounded border border-terminal-warmBorder uppercase">
                    {match.workplace_type}
                  </span>
                )}
              </div>

              <h1 className="text-2xl sm:text-3xl font-bold font-display text-terminal-dark tracking-tight leading-snug">
                {match.job_title || "Discovered Opportunity"}
              </h1>

              <div className="flex items-center gap-2 text-xs sm:text-sm text-terminal-muted flex-wrap font-sans">
                <span className="font-semibold text-terminal-dark flex items-center gap-1.5">
                  <Building2 className="w-4 h-4 text-terminal-muted" />
                  <span>{match.company_name || "Company"}</span>
                </span>
                <span>&bull;</span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4 text-terminal-muted" />
                  <span>{match.normalized_location || "Location not specified"}</span>
                </span>
                <span>&bull;</span>
                <span className="font-mono text-xs">
                  Evaluated: {formatDate(match.created_at)}
                </span>
              </div>

              {match.match_explanation && (
                <p className="text-xs sm:text-sm text-terminal-dark/90 font-sans italic bg-terminal-warm/60 p-3 rounded-card border border-terminal-warmBorder leading-relaxed">
                  "{match.match_explanation}"
                </p>
              )}
            </div>

            {/* Right: Scores & Actions */}
            <div className="flex flex-col items-start md:items-end justify-between shrink-0 gap-4 pt-3 md:pt-0 border-t md:border-t-0 border-terminal-warmBorder/60">
              <div className="flex flex-col items-start md:items-end">
                <span className="text-xs font-mono font-bold uppercase text-terminal-muted mb-1">
                  Overall Match Score
                </span>
                <MatchScoreBadge score={finalScore} size="lg" showLabel />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsTailorModalOpen(true)}
                  className="text-xs gap-1.5 shadow-subtle"
                  title="Generate truthful tailored ATS resume for this opportunity"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Tailor Resume</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReevaluate}
                  disabled={reevaluateMutation.isPending}
                  isLoading={reevaluateMutation.isPending}
                  className="text-xs gap-1.5"
                  title="Re-run Layer 1 & 2 evaluation with updated candidate profile"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Re-evaluate</span>
                </Button>

                <Link to={`/jobs/${match.job_id}`}>
                  <Button variant="outline" size="sm" className="text-xs gap-1.5">
                    <Briefcase className="w-3.5 h-3.5" />
                    <span>View Opportunity</span>
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. Layer 1: Deterministic Eligibility Evaluation Section */}
      <Card className="border-terminal-warmBorder">
        <CardHeader className="pb-3 border-b border-terminal-warmBorder/60">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              {isEligible ? (
                <ShieldCheck className="w-4 h-4 text-terminal-success" />
              ) : (
                <ShieldAlert className="w-4 h-4 text-terminal-error" />
              )}
              <span>Layer 1: Deterministic Eligibility Audit</span>
            </CardTitle>
            <EligibilityBadge status={match.eligibility_status} />
          </div>
          <CardDescription className="text-xs">
            Hard boolean gating checks enforcing legal work authorization, experience floors, and location restrictions
          </CardDescription>
        </CardHeader>

        <CardContent className="p-6">
          {isEligible ? (
            <div className="flex items-start gap-3 p-4 rounded-card bg-[#5BCB8A]/10 border border-[#5BCB8A]/30 text-xs">
              <CheckCircle2 className="w-4 h-4 text-[#185C36] shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-[#185C36]">All Mandatory Eligibility Criteria Satisfied</span>
                <p className="text-terminal-dark/80 mt-1 font-sans">
                  The candidate satisfies work authorization, minimum experience requirements, and geographic criteria for this opportunity. This job advances to Layer 2 weighted scoring.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 p-4 rounded-card bg-terminal-error/10 border border-terminal-error/30 text-xs">
              <XCircle className="w-4 h-4 text-terminal-error shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-terminal-errorText">Disqualified by Mandatory Eligibility Gating</span>
                <p className="text-terminal-dark/80 mt-1 font-sans leading-relaxed">
                  {eligDetails?.explanation || match.match_explanation || "Disqualified by Layer 1 deterministic checks."}
                </p>
                <p className="text-terminal-muted text-[11px] mt-2 font-mono">
                  * Note: Ineligible opportunities are disqualified from qualification and resume tailoring, regardless of candidate skill overlap.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 3. Layer 2: Deterministic Score Breakdown */}
      <DeterministicScoreBreakdown match={match} />

      {/* 4. Layer 3: LLM Semantic Analysis */}
      <SemanticAnalysisSection
        match={match}
        onTriggerSemanticAnalysis={handleTriggerSemantic}
        isTriggering={semanticMutation.isPending}
      />

      {/* 5. Related Canonical Job Summary */}
      {match.job && (
        <Card className="border-terminal-warmBorder">
          <CardHeader className="pb-3 border-b border-terminal-warmBorder/60">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <FileText className="w-4 h-4 text-terminal-primary" />
                <span>Related Canonical Job Information</span>
              </CardTitle>
              <Link to={`/jobs/${match.job_id}`}>
                <Button variant="outline" size="sm" className="text-xs gap-1">
                  <span>Full Job Details</span>
                  <ExternalLink className="w-3 h-3" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-3">
            <div className="flex items-center gap-3 text-xs text-terminal-muted font-sans flex-wrap">
              <span className="font-semibold text-terminal-dark">{match.job.title}</span>
              <span>&bull;</span>
              <span>{match.job.canonical_company_name}</span>
              <span>&bull;</span>
              <span>{match.job.normalized_location || "Location not specified"}</span>
            </div>

            {match.job.canonical_application_url && (
              <div className="pt-2">
                <a
                  href={match.job.canonical_application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-terminal-primary hover:underline"
                >
                  <span>Apply Directly on Upstream Career Page</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tailor Resume Modal */}
      {isTailorModalOpen && (
        <TailorResumeModal
          isOpen={isTailorModalOpen}
          onClose={() => setIsTailorModalOpen(false)}
          jobId={match.job_id}
          jobTitle={match.job_title ?? undefined}
          companyName={match.company_name ?? undefined}
          jobMatchId={match.id}
          isQualified={match.is_qualified}
        />
      )}
    </div>
  );
}
