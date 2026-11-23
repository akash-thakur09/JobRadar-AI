import { Link } from "react-router-dom";
import {
  Building2,
  MapPin,
  Sparkles,
  ArrowRight,
  Brain,
} from "lucide-react";
import type { JobMatchSummary } from "@/types/matches";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";
import { EligibilityBadge } from "./EligibilityBadge";
import { MatchScoreBadge } from "./MatchScoreBadge";

export interface MatchCardProps {
  match: JobMatchSummary;
}

export function MatchCard({ match }: MatchCardProps) {
  const finalScore = Number(match.final_score) || 0;
  const detScore = Number(match.deterministic_score) || 0;
  const semScore = match.semantic_score !== null ? Number(match.semantic_score) : null;

  const hasSemantic = match.semantic_analysis_status === "COMPLETED" && semScore !== null;

  return (
    <Card className="hover:border-terminal-muted/60 transition-all shadow-subtle group">
      <CardContent className="p-5 flex flex-col md:flex-row items-start justify-between gap-4">
        {/* Left Column: Match & Job Information */}
        <div className="space-y-3 flex-1 min-w-0">
          {/* Header Badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <EligibilityBadge status={match.eligibility_status} />

            {match.semantic_analysis_status === "COMPLETED" ? (
              <Badge variant="brand" className="gap-1 font-mono text-[10px] bg-[#8DB4FF]/15 text-[#1E3A8A] border-[#8DB4FF]/40">
                <Sparkles className="w-3 h-3 text-[#1E3A8A]" />
                <span>AI Semantic Evaluated</span>
              </Badge>
            ) : match.semantic_analysis_status === "PROCESSING" ? (
              <Badge variant="warning" className="gap-1 font-mono text-[10px] animate-pulse">
                <Brain className="w-3 h-3" />
                <span>AI Analyzing...</span>
              </Badge>
            ) : match.semantic_analysis_status === "SKIPPED" ? (
              <Badge variant="neutral" className="font-mono text-[10px]">
                <span>LLM Skipped (&lt;50%)</span>
              </Badge>
            ) : null}

            {match.workplace_type && (
              <span className="text-[10px] font-mono text-terminal-muted bg-terminal-warm px-2 py-0.5 rounded border border-terminal-warmBorder uppercase">
                {match.workplace_type}
              </span>
            )}
          </div>

          {/* Job Title & Company */}
          <div>
            <h3 className="text-base sm:text-lg font-bold font-display text-terminal-dark group-hover:text-terminal-primary transition-colors leading-snug">
              <Link to={`/matches/${match.id}`} className="hover:underline">
                {match.job_title || "Discovered Opportunity"}
              </Link>
            </h3>

            <div className="flex items-center gap-2 text-xs text-terminal-muted mt-1 font-sans flex-wrap">
              <span className="font-semibold text-terminal-dark flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5 text-terminal-muted" />
                <span>{match.company_name || "Company"}</span>
              </span>

              <span>&bull;</span>

              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-terminal-muted" />
                <span>{match.normalized_location || "Location not specified"}</span>
              </span>

              <span>&bull;</span>

              <span className="font-mono text-[11px]">
                Evaluated: {formatDate(match.created_at)}
              </span>
            </div>
          </div>

          {/* Explanation Quote */}
          {match.match_explanation && (
            <p className="text-xs text-terminal-dark/80 italic font-sans line-clamp-2 bg-terminal-warm/40 p-2.5 rounded border border-terminal-warmBorder/60">
              "{match.match_explanation}"
            </p>
          )}

          {/* Score breakdown chips */}
          <div className="flex items-center gap-2 flex-wrap text-[11px] font-mono">
            <span className="px-2 py-0.5 rounded bg-terminal-warm border border-terminal-warmBorder text-terminal-dark">
              Det: <span className="font-bold">{detScore.toFixed(0)}</span>/100
            </span>

            {hasSemantic && (
              <span className="px-2 py-0.5 rounded bg-[#8DB4FF]/15 text-[#1E3A8A] border border-[#8DB4FF]/30">
                LLM: <span className="font-bold">{semScore.toFixed(0)}</span>/100
              </span>
            )}

            <span className="text-terminal-muted">
              Skills: <span className="text-terminal-dark font-medium">{Number(match.skill_score).toFixed(0)}/40</span>
            </span>
            <span>&bull;</span>
            <span className="text-terminal-muted">
              Exp: <span className="text-terminal-dark font-medium">{Number(match.experience_score).toFixed(0)}/20</span>
            </span>
            <span>&bull;</span>
            <span className="text-terminal-muted">
              Title: <span className="text-terminal-dark font-medium">{Number(match.title_score).toFixed(0)}/15</span>
            </span>
          </div>
        </div>

        {/* Right Column: Score & Action CTA */}
        <div className="flex md:flex-col items-center md:items-end justify-between md:justify-center gap-3 shrink-0 w-full md:w-auto pt-2 md:pt-0 border-t md:border-t-0 border-terminal-warmBorder/60">
          <div className="flex flex-col items-start md:items-end">
            <span className="text-[10px] font-mono font-bold uppercase text-terminal-muted mb-1">
              Final Relevance
            </span>
            <MatchScoreBadge score={finalScore} size="lg" showLabel />
          </div>

          <div className="flex items-center gap-2">
            <Link to={`/matches/${match.id}`}>
              <Button variant="primary" size="sm" className="text-xs gap-1 shadow-subtle font-sans">
                <span>Inspect Match</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>

            <Link to={`/jobs/${match.job_id}`}>
              <Button variant="outline" size="sm" className="text-xs font-sans" title="View canonical job posting">
                <span>Job</span>
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
