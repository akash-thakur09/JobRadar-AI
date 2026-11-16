import {
  Brain,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ArrowRightLeft,
  ShieldCheck,
  RefreshCw,
  Info,
} from "lucide-react";
import type { JobMatchDetail } from "@/types/matches";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export interface SemanticAnalysisSectionProps {
  match: JobMatchDetail;
  onTriggerSemanticAnalysis: () => void;
  isTriggering: boolean;
}

export function SemanticAnalysisSection({
  match,
  onTriggerSemanticAnalysis,
  isTriggering,
}: SemanticAnalysisSectionProps) {
  const status = match.semantic_analysis_status;
  const semScore = match.semantic_score !== null ? Number(match.semantic_score) : null;
  const semDetails = match.match_explanation_details?.semantic_evaluation;

  const recommendation = semDetails?.recommendation || "NOT_SPECIFIED";
  const confidence = semDetails?.confidence ? Math.round(semDetails.confidence * 100) : null;
  const strengths = semDetails?.strengths || [];
  const gaps = semDetails?.gaps || [];
  const transferableSkills = semDetails?.transferable_skills || [];

  const getRecommendationBadge = (rec: string) => {
    switch (rec) {
      case "STRONG_MATCH":
        return (
          <Badge variant="success" className="font-mono text-xs uppercase px-2.5 py-1">
            Strong Match Recommendation
          </Badge>
        );
      case "GOOD_MATCH":
        return (
          <Badge variant="brand" className="font-mono text-xs uppercase px-2.5 py-1">
            Good Match Recommendation
          </Badge>
        );
      case "BORDERLINE":
        return (
          <Badge variant="warning" className="font-mono text-xs uppercase px-2.5 py-1">
            Borderline Fit
          </Badge>
        );
      case "NOT_RECOMMENDED":
        return (
          <Badge variant="danger" className="font-mono text-xs uppercase px-2.5 py-1">
            Not Recommended
          </Badge>
        );
      default:
        return (
          <Badge variant="neutral" className="font-mono text-xs uppercase px-2.5 py-1">
            {rec.replace(/_/g, " ")}
          </Badge>
        );
    }
  };

  const getImpactBadgeVariant = (impact?: string) => {
    switch (impact?.toUpperCase()) {
      case "HIGH":
        return "danger";
      case "MEDIUM":
        return "warning";
      case "LOW":
        return "neutral";
      default:
        return "neutral";
    }
  };

  return (
    <Card className="border-terminal-warmBorder">
      <CardHeader className="pb-3 border-b border-terminal-warmBorder/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Brain className="w-4 h-4 text-terminal-primary" />
              <span>Layer 3: LLM Semantic Analysis & Contextual Intelligence</span>
            </CardTitle>
            <CardDescription className="text-xs">
              Contextual synthesis via local Ollama LLM evaluating transferable skills and evidence alignment
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            {status === "COMPLETED" && semScore !== null ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-terminal-muted">LLM Score:</span>
                <span className="text-base font-mono font-bold text-terminal-dark px-2.5 py-0.5 rounded-card bg-[#8DB4FF]/20 border border-[#8DB4FF]/40 text-[#1E3A8A]">
                  {semScore.toFixed(2)} / 100.00
                </span>
              </div>
            ) : (
              <Badge variant="neutral" className="font-mono text-xs uppercase">
                Status: {status}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-6">
        {status === "COMPLETED" && semDetails ? (
          <div className="space-y-6">
            {/* Header: Recommendation & Confidence */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder">
              <div className="flex items-center gap-3">
                {getRecommendationBadge(recommendation)}
                {confidence !== null && (
                  <span className="text-xs font-mono text-terminal-muted">
                    Confidence: <span className="font-bold text-terminal-dark">{confidence}%</span>
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5 text-xs text-[#185C36] font-medium">
                <ShieldCheck className="w-4 h-4" />
                <span>Evidence Vault Verified</span>
              </div>
            </div>

            {/* Executive Reasoning Summary */}
            {semDetails.reasoning_summary && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted">
                  Executive Alignment Summary
                </h4>
                <p className="text-xs sm:text-sm text-terminal-dark leading-relaxed font-sans bg-terminal-warmSurface p-4 rounded-card border border-terminal-warmBorder">
                  {semDetails.reasoning_summary}
                </p>
              </div>
            )}

            {/* Strengths Breakdown */}
            {strengths.length > 0 && (
              <div className="space-y-2.5">
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-terminal-success" />
                  <span>Demonstrated Core Strengths ({strengths.length})</span>
                </h4>
                <div className="grid grid-cols-1 gap-2.5">
                  {strengths.map((str, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface space-y-1.5 text-xs font-sans"
                    >
                      <div className="font-semibold text-terminal-dark">{str.claim}</div>
                      {str.evidence && (
                        <div className="text-[11px] text-terminal-muted font-sans flex items-start gap-1">
                          <span className="font-semibold text-terminal-dark shrink-0">Candidate Evidence:</span>
                          <span>{str.evidence}</span>
                        </div>
                      )}
                      {str.job_context && (
                        <div className="text-[11px] text-terminal-muted font-sans flex items-start gap-1">
                          <span className="font-semibold text-terminal-dark shrink-0">JD Relevance:</span>
                          <span>{str.job_context}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Transferable Skills */}
            {transferableSkills.length > 0 && (
              <div className="space-y-2.5">
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted flex items-center gap-1.5">
                  <ArrowRightLeft className="w-3.5 h-3.5 text-terminal-primary" />
                  <span>Transferable Skills & Architectural Substitution ({transferableSkills.length})</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {transferableSkills.map((ts, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-card border border-[#8DB4FF]/40 bg-[#8DB4FF]/10 space-y-1.5 text-xs"
                    >
                      <div className="flex items-center gap-2 font-mono">
                        <span className="font-bold text-terminal-dark bg-white px-2 py-0.5 rounded border border-terminal-warmBorder">
                          {ts.candidate_skill}
                        </span>
                        <span className="text-terminal-muted">&rarr;</span>
                        <span className="font-bold text-terminal-primary bg-white px-2 py-0.5 rounded border border-terminal-warmBorder">
                          {ts.target_technology}
                        </span>
                      </div>
                      {ts.rationale && (
                        <p className="text-[11px] text-terminal-dark font-sans leading-normal">
                          {ts.rationale}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Gaps & Unmet Requirements */}
            {gaps.length > 0 && (
              <div className="space-y-2.5">
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-terminal-amber" />
                  <span>Identified Gaps & Unverified Requirements ({gaps.length})</span>
                </h4>
                <div className="grid grid-cols-1 gap-2.5">
                  {gaps.map((gap, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface space-y-1.5 text-xs font-sans"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-terminal-dark">{gap.gap}</span>
                        <Badge variant={getImpactBadgeVariant(gap.impact)} className="text-[10px] font-mono uppercase">
                          Impact: {gap.impact || "MEDIUM"}
                        </Badge>
                      </div>
                      {gap.mitigation && (
                        <div className="text-[11px] text-terminal-muted flex items-start gap-1 font-sans">
                          <span className="font-semibold text-terminal-dark shrink-0">Softening Mitigation:</span>
                          <span>{gap.mitigation}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Formula Note */}
            <div className="p-3 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder text-xs text-terminal-muted font-mono flex items-center gap-2">
              <Info className="w-4 h-4 text-terminal-primary shrink-0" />
              <span>
                Final Hybrid Score = (60% &times; Deterministic Score) + (40% &times; LLM Semantic Score) = {Number(match.final_score).toFixed(2)}/100
              </span>
            </div>
          </div>
        ) : status === "PROCESSING" ? (
          <div className="py-10 text-center space-y-3">
            <RefreshCw className="w-8 h-8 text-terminal-primary animate-spin mx-auto" />
            <h4 className="text-sm font-bold font-display text-terminal-dark">Analyzing with Ollama LLM...</h4>
            <p className="text-xs text-terminal-muted max-w-sm mx-auto font-sans">
              Layer 3 semantic analysis is evaluating context, transferable skills, and candidate profile alignment.
            </p>
          </div>
        ) : status === "SKIPPED" ? (
          <div className="p-5 text-center rounded-card bg-terminal-warm/40 border border-terminal-warmBorder space-y-2">
            <Info className="w-6 h-6 text-terminal-muted mx-auto" />
            <h4 className="text-sm font-semibold text-terminal-dark">Semantic Analysis Skipped</h4>
            <p className="text-xs text-terminal-muted max-w-md mx-auto font-sans">
              Layer 3 LLM evaluation is reserved for qualified opportunities with deterministic score &ge; 50.00. 
              The current deterministic score is {Number(match.deterministic_score).toFixed(1)}/100.
            </p>
          </div>
        ) : (
          /* PENDING or FAILED */
          <div className="p-6 text-center rounded-card bg-terminal-warm/40 border border-terminal-warmBorder space-y-3">
            <Brain className="w-7 h-7 text-terminal-muted mx-auto" />
            <h4 className="text-sm font-semibold text-terminal-dark">
              {status === "FAILED" ? "Semantic Analysis Failed or Degraded" : "Semantic Analysis Not Yet Run"}
            </h4>
            <p className="text-xs text-terminal-muted max-w-md mx-auto font-sans">
              {status === "FAILED"
                ? "The previous LLM invocation timed out or encountered an error. The system gracefully degraded to the deterministic score. You can re-trigger semantic analysis now."
                : "Trigger Layer 3 LLM Semantic Analysis to evaluate contextual nuances and transferable skills."}
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={onTriggerSemanticAnalysis}
              disabled={isTriggering}
              isLoading={isTriggering}
              className="gap-1.5 text-xs shadow-subtle"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Run Layer 3 Semantic Analysis</span>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

