import { readPageParam } from "@/lib/utils";
import { useSearchParams, Link } from "react-router-dom";
import { Play, RefreshCw, FolderOpen } from "lucide-react";
import { useMatches } from "@/hooks/useMatches";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/Button";
import { MatchCard } from "../components/MatchCard";
import { MatchFilters } from "../components/MatchFilters";
import type { EligibilityStatus } from "@/types/matches";

const PAGE_SIZE = 15;

export function MatchesPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Read URL search params
  const minScore = searchParams.get("min_score") || "";
  const eligibility = searchParams.get("eligibility") || "";
  const page = readPageParam(searchParams.get("page"));

  const {
    data: matchesResponse,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useMatches({
    page,
    page_size: PAGE_SIZE,
    min_score: minScore ? parseFloat(minScore) : undefined,
    eligibility: (eligibility as EligibilityStatus) || undefined,
  });

  const updateParams = (newParams: Record<string, string | null>) => {
    const updated = new URLSearchParams(searchParams);
    Object.entries(newParams).forEach(([key, val]) => {
      if (val === null || val === "") {
        updated.delete(key);
      } else {
        updated.set(key, val);
      }
    });
    setSearchParams(updated);
  };

  const handleMinScoreChange = (score: string) => {
    updateParams({ min_score: score || null, page: "1" });
  };

  const handleEligibilityChange = (elig: string) => {
    updateParams({ eligibility: elig || null, page: "1" });
  };

  const handleResetFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  const handlePageChange = (newPage: number) => {
    updateParams({ page: String(newPage) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const matches = matchesResponse?.items || [];
  const pagination = matchesResponse?.pagination;
  const totalItems = pagination?.total_items || 0;
  const totalPages = pagination?.total_pages || 0;
  const hasNext = Boolean(pagination?.has_next);
  const hasPrev = Boolean(pagination?.has_prev);

  const hasActiveFilters = Boolean(minScore || eligibility);

  // Derive metrics from current page
  const qualifiedCount = matches.filter((m) => m.is_qualified || (Number(m.final_score) >= 50 && m.eligibility_status === "ELIGIBLE")).length;
  const topScore = matches.length > 0 ? Math.max(...matches.map((m) => Number(m.final_score) || 0)) : 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Job Matches"
        subtitle="Candidate-specific match intelligence scored across Layer 1 eligibility, Layer 2 deterministic scoring, and Layer 3 semantic analysis"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Job Matches" },
        ]}
        actions={
          <Link to="/pipeline">
            <Button variant="primary" size="sm" className="text-xs gap-1.5 shadow-subtle">
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Trigger Pipeline Run</span>
            </Button>
          </Link>
        }
      />

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle">
          <span className="text-[11px] font-mono font-bold uppercase text-terminal-muted block mb-1">
            Total Evaluated
          </span>
          <div className="text-2xl font-bold font-mono text-terminal-dark">
            {totalItems}
          </div>
        </div>

        <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle">
          <span className="text-[11px] font-mono font-bold uppercase text-terminal-muted block mb-1">
            Qualified on Page
          </span>
          <div className="text-2xl font-bold font-mono text-[#185C36]">
            {qualifiedCount}
          </div>
        </div>

        <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle">
          <span className="text-[11px] font-mono font-bold uppercase text-terminal-muted block mb-1">
            Top Match Score
          </span>
          <div className="text-2xl font-bold font-mono text-terminal-primary">
            {topScore > 0 ? `${Math.round(topScore)}%` : "—"}
          </div>
        </div>

        <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle">
          <span className="text-[11px] font-mono font-bold uppercase text-terminal-muted block mb-1">
            Scoring Policy
          </span>
          <div className="text-xs font-mono font-semibold text-terminal-dark mt-1">
            60% Det + 40% LLM
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <MatchFilters
        minScore={minScore}
        eligibility={eligibility}
        onMinScoreChange={handleMinScoreChange}
        onEligibilityChange={handleEligibilityChange}
        onReset={handleResetFilters}
      />

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-terminal-muted px-1">
        <div className="flex items-center gap-2">
          <span>
            {totalItems > 0 ? (
              <>
                Showing <span className="font-mono font-bold text-terminal-dark">{(page - 1) * PAGE_SIZE + 1}</span>–
                <span className="font-mono font-bold text-terminal-dark">
                  {Math.min(page * PAGE_SIZE, totalItems)}
                </span> of <span className="font-mono font-bold text-terminal-dark">{totalItems}</span> match evaluations
              </>
            ) : (
              "No match evaluations found"
            )}
          </span>
          {isFetching && !isLoading && (
            <span className="font-mono text-[11px] text-terminal-primary animate-pulse flex items-center gap-1">
              <RefreshCw className="w-3 h-3 animate-spin" />
              <span>Updating...</span>
            </span>
          )}
        </div>

        {totalPages > 1 && (
          <span className="font-mono text-[11px]">
            Page {page} of {totalPages}
          </span>
        )}
      </div>

      {/* Content State Handling */}
      {isLoading ? (
        <LoadingState message="Fetching candidate match evaluations..." />
      ) : error ? (
        <ErrorState
          title="Failed to Load Matches"
          message="Could not retrieve job matches for candidate. Ensure backend database and Redis services are reachable."
          onRetry={() => refetch()}
        />
      ) : matches.length === 0 ? (
        <EmptyState
          icon={FolderOpen}
          title={hasActiveFilters ? "No matching evaluations" : "No match evaluations recorded yet"}
          description={
            hasActiveFilters
              ? "No job matches satisfied your current score threshold and eligibility filters. Try resetting the filters."
              : "Execute a pipeline run to evaluate discovered canonical job opportunities against your profile."
          }
          action={
            hasActiveFilters ? (
              <Button variant="outline" size="sm" onClick={handleResetFilters}>
                Clear All Filters
              </Button>
            ) : (
              <Link to="/pipeline">
                <Button variant="primary" size="sm">
                  Trigger Pipeline Run
                </Button>
              </Link>
            )
          }
        />
      ) : (
        <div className="space-y-3">
          {matches.map((match) => (
            <MatchCard key={match.id} match={match} />
          ))}

          {/* Server-Side Pagination Bar */}
          {totalPages > 1 && (
            <div className="pt-4 flex items-center justify-between border-t border-terminal-warmBorder">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(page - 1)}
                disabled={!hasPrev || isFetching}
                className="text-xs font-mono"
              >
                &larr; Previous
              </Button>

              <div className="flex items-center gap-1">
                <span className="text-xs font-mono text-terminal-muted">
                  Page <span className="text-terminal-dark font-bold">{page}</span> of {totalPages}
                </span>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(page + 1)}
                disabled={!hasNext || isFetching}
                className="text-xs font-mono"
              >
                Next &rarr;
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
