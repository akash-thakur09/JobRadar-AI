import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, CheckCircle2, XCircle, FolderOpen } from "lucide-react";
import { useMatches } from "@/hooks/useMatches";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";

export function RecentMatchesCard() {
  const { data: matchesResponse, isLoading, error } = useMatches({ page_size: 5 });

  const matches = matchesResponse?.items || [];
  const totalMatches = matchesResponse?.pagination?.total_items || 0;

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-terminal-primary" />
            <span>Recent Match Evaluations</span>
          </CardTitle>
          <CardDescription>
            {totalMatches > 0
              ? `${totalMatches} opportunities evaluated across Layer 1 & 2 matching`
              : "Candidate-specific intelligence scoring"}
          </CardDescription>
        </div>
        <Link
          to="/matches"
          className="text-xs font-mono font-medium text-terminal-primary hover:text-terminal-primaryHover flex items-center gap-1 shrink-0 pt-0.5"
        >
          <span>Explore All</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col justify-between">
        {isLoading ? (
          <div className="py-12 flex justify-center items-center">
            <Spinner size="md" label="Loading match evaluations..." />
          </div>
        ) : error ? (
          <div className="p-4 rounded-card bg-terminal-error/10 border border-terminal-error/30 text-terminal-errorText text-xs font-mono text-center">
            Unable to fetch match evaluations. Please verify backend state.
          </div>
        ) : matches.length === 0 ? (
          <div className="text-center py-8 rounded-card border-2 border-dashed border-terminal-warmBorder bg-terminal-warm/20 p-5">
            <FolderOpen className="w-6 h-6 text-terminal-muted mx-auto mb-2" />
            <p className="text-xs font-medium text-terminal-dark font-display">No matches evaluated yet</p>
            <p className="text-[11px] text-terminal-muted mt-0.5 max-w-xs mx-auto">
              Execute a pipeline run to evaluate discovered jobs against your verified profile.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-terminal-warmBorder/60">
            {matches.map((match) => {
              const scoreNum = Number(match.final_score) || 0;
              const isEligible = match.eligibility_status === "ELIGIBLE";

              return (
                <div
                  key={match.id}
                  className="py-3 first:pt-0 last:pb-0 flex items-start justify-between gap-3 group"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-xs font-semibold font-display text-terminal-dark truncate group-hover:text-terminal-primary transition-colors">
                        {match.job_title || "Discovered Opportunity"}
                      </h4>
                      {isEligible ? (
                        <Badge variant="success" className="text-[10px] py-0 px-1.5 gap-1">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                          <span>Eligible</span>
                        </Badge>
                      ) : (
                        <Badge variant="danger" className="text-[10px] py-0 px-1.5 gap-1">
                          <XCircle className="w-2.5 h-2.5" />
                          <span>Ineligible</span>
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-terminal-muted mt-1 font-sans flex-wrap">
                      <span className="font-medium text-terminal-dark">
                        {match.company_name || "Company"}
                      </span>
                      <span>&bull;</span>
                      <span>{match.normalized_location || "Remote"}</span>
                      <span>&bull;</span>
                      <span className="font-mono text-[10px]">{formatDate(match.created_at)}</span>
                    </div>

                    {match.match_explanation && (
                      <p className="text-[11px] text-terminal-muted mt-1.5 line-clamp-1 italic font-sans">
                        "{match.match_explanation}"
                      </p>
                    )}
                  </div>

                  {/* Score Pill */}
                  <div className="shrink-0 text-right">
                    <span
                      className={`inline-block px-2.5 py-1 rounded-card font-mono text-xs font-bold border ${
                        scoreNum >= 75
                          ? "bg-[#D6FF3F]/25 text-[#3B4D00] border-[#B8E61A]/50"
                          : scoreNum >= 50
                          ? "bg-[#8DB4FF]/15 text-[#183B7E] border-[#8DB4FF]/40"
                          : "bg-terminal-warm border-terminal-warmBorder text-terminal-muted"
                      }`}
                    >
                      {scoreNum.toFixed(0)}%
                    </span>
                    <span className="block text-[9px] font-mono uppercase text-terminal-muted mt-0.5">
                      relevance
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="pt-3 mt-3 border-t border-terminal-warmBorder flex items-center justify-between text-[11px] font-mono text-terminal-muted">
          <span>Scoring: Trigram + Seniority + Skills</span>
          <Link to="/matches" className="hover:text-terminal-dark transition-colors">
            View match details &rarr;
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

