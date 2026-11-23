import { readPageParam } from "@/lib/utils";
import { useSearchParams } from "react-router-dom";
import { Briefcase, RefreshCw } from "lucide-react";
import { useJobs, useProcessPendingJobs } from "@/hooks/useJobs";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/Button";
import { JobCard } from "../components/JobCard";
import { JobFilters } from "../components/JobFilters";
import type { JobStatus } from "@/types/jobs";
import type { WorkplaceType } from "@/types/candidate";

const PAGE_SIZE = 15;

export function JobsDiscoveryPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Read URL search params
  const search = searchParams.get("search") || "";
  const workplaceType = searchParams.get("workplace") || "";
  const status = searchParams.get("status") || "";
  const page = readPageParam(searchParams.get("page"));

  const {
    data: jobsResponse,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useJobs({
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    workplace_type: (workplaceType as WorkplaceType) || undefined,
    status: (status as JobStatus) || undefined,
  });

  const processPendingMutation = useProcessPendingJobs();

  // URL state update helpers
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

  const handleSearchChange = (newSearch: string) => {
    updateParams({ search: newSearch || null, page: "1" });
  };

  const handleWorkplaceChange = (newWp: string) => {
    updateParams({ workplace: newWp || null, page: "1" });
  };

  const handleStatusChange = (newStatus: string) => {
    updateParams({ status: newStatus || null, page: "1" });
  };

  const handleResetFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  const handlePageChange = (newPage: number) => {
    updateParams({ page: String(newPage) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleProcessPending = async () => {
    try {
      await processPendingMutation.mutateAsync(100);
      refetch();
    } catch {
      // Handled by react query mutation state
    }
  };

  const jobs = jobsResponse?.items || [];
  const pagination = jobsResponse?.pagination;
  const totalItems = pagination?.total_items || 0;
  const totalPages = pagination?.total_pages || 0;
  const hasNext = Boolean(pagination?.has_next);
  const hasPrev = Boolean(pagination?.has_prev);

  const hasActiveFilters = Boolean(search || workplaceType || status);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Job Discovery"
        subtitle="Explore clean, deduplicated canonical opportunities ingested across company careers pages and ATS feeds"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Job Discovery" },
        ]}
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={handleProcessPending}
              disabled={processPendingMutation.isPending}
              isLoading={processPendingMutation.isPending}
              className="text-xs gap-1.5"
              title="Canonicalize newly ingested raw postings"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Process Pending</span>
            </Button>
          </div>
        }
      />

      {/* Filters Bar */}
      <JobFilters
        search={search}
        workplaceType={workplaceType}
        status={status}
        onSearchChange={handleSearchChange}
        onWorkplaceTypeChange={handleWorkplaceChange}
        onStatusChange={handleStatusChange}
        onReset={handleResetFilters}
      />

      {/* Results Header & Telemetry */}
      <div className="flex items-center justify-between text-xs text-terminal-muted px-1">
        <div className="flex items-center gap-2">
          <span>
            {totalItems > 0 ? (
              <>
                Showing <span className="font-mono font-bold text-terminal-dark">{(page - 1) * PAGE_SIZE + 1}</span>–
                <span className="font-mono font-bold text-terminal-dark">
                  {Math.min(page * PAGE_SIZE, totalItems)}
                </span> of <span className="font-mono font-bold text-terminal-dark">{totalItems}</span> opportunities
              </>
            ) : (
              "No opportunities found"
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
        <LoadingState message="Querying canonical job opportunities..." />
      ) : error ? (
        <ErrorState
          title="Failed to Load Jobs"
          message="An error occurred while connecting to the canonical jobs repository. Please check your backend connection."
          onRetry={() => refetch()}
        />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title={hasActiveFilters ? "No matching opportunities" : "No canonical jobs discovered yet"}
          description={
            hasActiveFilters
              ? "No job postings matched your current search and workplace filters. Try broadening your criteria."
              : "Execute a pipeline discovery run or process pending raw source records to populate canonical jobs."
          }
          action={
            hasActiveFilters ? (
              <Button variant="outline" size="sm" onClick={handleResetFilters}>
                Clear All Filters
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleProcessPending}
                disabled={processPendingMutation.isPending}
              >
                Process Pending Records
              </Button>
            )
          }
        />
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
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
