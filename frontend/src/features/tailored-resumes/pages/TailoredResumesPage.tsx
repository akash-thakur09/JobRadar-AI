import { readPageParam } from "@/lib/utils";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Sparkles,
  FileText,
  Globe,
  ChevronLeft,
  ChevronRight,
  Filter,
  FileCheck,
} from "lucide-react";
import { useTailoredResumes } from "@/hooks/useTailoredResumes";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { TailoredResumeCard } from "../components/TailoredResumeCard";

const PAGE_SIZE = 10;

export function TailoredResumesPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = readPageParam(searchParams.get("page"));
  const statusFilter = searchParams.get("status") || "ALL";

  const { data: response, isLoading, error, refetch } = useTailoredResumes({
    page,
    page_size: PAGE_SIZE,
  });

  const allItems = useMemo(() => response?.items || [], [response]);
  const total = response?.pagination?.total_items || 0;
  const totalPages = response?.pagination?.total_pages || Math.ceil(total / PAGE_SIZE) || 1;

  // Filter items by client-side status filter if specified
  const filteredItems = useMemo(() => {
    if (statusFilter === "ALL") return allItems;
    if (statusFilter === "COMPLETED") {
      return allItems.filter((i) => i.generation_status === "COMPLETED");
    }
    if (statusFilter === "PROCESSING") {
      return allItems.filter(
        (i) =>
          i.generation_status === "PENDING" ||
          i.generation_status === "PROCESSING" ||
          i.generation_status === "VALIDATING" ||
          i.generation_status === "RENDERING"
      );
    }
    if (statusFilter === "FAILED") {
      return allItems.filter((i) => i.generation_status === "FAILED");
    }
    return allItems;
  }, [allItems, statusFilter]);

  // Aggregate stats
  const completedCount = allItems.filter((i) => i.generation_status === "COMPLETED").length;
  const inProgressCount = allItems.filter(
    (i) =>
      i.generation_status === "PENDING" ||
      i.generation_status === "PROCESSING" ||
      i.generation_status === "VALIDATING" ||
      i.generation_status === "RENDERING"
  ).length;
  const failedCount = allItems.filter((i) => i.generation_status === "FAILED").length;

  const handleStatusFilterChange = (newStatus: string) => {
    const updated = new URLSearchParams(searchParams);
    if (newStatus === "ALL") {
      updated.delete("status");
    } else {
      updated.set("status", newStatus);
    }
    setSearchParams(updated);
  };

  const handlePageChange = (newPage: number) => {
    const updated = new URLSearchParams(searchParams);
    updated.set("page", String(newPage));
    setSearchParams(updated);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tailored Resumes"
        description="Inspect truthful, ATS-optimized resumes tailored for specific canonical jobs. Each document includes full claim validation audits."
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Resumes", href: "/resumes" },
          { label: "Tailored Resumes" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Link to="/resumes">
              <Button variant="outline" size="sm">
                <FileText className="w-3.5 h-3.5" />
                Master Resumes
              </Button>
            </Link>
            <Link to="/jobs">
              <Button variant="primary" size="sm">
                <Globe className="w-3.5 h-3.5" />
                Find Jobs to Tailor
              </Button>
            </Link>
          </div>
        }
      />

      {/* Summary KPI Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="bg-terminal-warmSurface">
          <CardContent className="p-3.5">
            <span className="text-[10px] uppercase font-mono tracking-wider text-terminal-muted">
              Total Tailored
            </span>
            <div className="text-xl font-bold font-display text-terminal-dark mt-0.5">{total}</div>
          </CardContent>
        </Card>

        <Card className="bg-terminal-warmSurface border-l-4 border-l-terminal-success">
          <CardContent className="p-3.5">
            <span className="text-[10px] uppercase font-mono tracking-wider text-terminal-muted">
              ATS Ready
            </span>
            <div className="text-xl font-bold font-display text-terminal-success mt-0.5">
              {completedCount}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-terminal-warmSurface border-l-4 border-l-terminal-warning">
          <CardContent className="p-3.5">
            <span className="text-[10px] uppercase font-mono tracking-wider text-terminal-muted">
              In Pipeline
            </span>
            <div className="text-xl font-bold font-display text-terminal-warning mt-0.5">
              {inProgressCount}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-terminal-warmSurface border-l-4 border-l-terminal-error">
          <CardContent className="p-3.5">
            <span className="text-[10px] uppercase font-mono tracking-wider text-terminal-muted">
              Validation Flags
            </span>
            <div className="text-xl font-bold font-display text-terminal-error mt-0.5">
              {failedCount}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-terminal-warm rounded-card border border-terminal-warmBorder">
        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-terminal-muted" />
          <span className="text-xs font-semibold text-terminal-dark">Status:</span>
          {(["ALL", "COMPLETED", "PROCESSING", "FAILED"] as const).map((st) => (
            <button
              key={st}
              onClick={() => handleStatusFilterChange(st)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                statusFilter === st
                  ? "bg-terminal-dark text-white shadow-xs"
                  : "text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warmSurface"
              }`}
            >
              {st === "ALL" ? "All" : st === "COMPLETED" ? "Ready" : st === "PROCESSING" ? "In Progress" : "Failed"}
            </button>
          ))}
        </div>

        <span className="text-xs text-terminal-muted font-mono">
          Showing {filteredItems.length} records
        </span>
      </div>

      {isLoading && <LoadingState message="Loading tailored resume applications..." />}

      {error && (
        <ErrorState
          title="Failed to Load Tailored Resumes"
          message="Could not retrieve tailored resumes. Verify backend connection."
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !error && filteredItems.length === 0 && (
        <EmptyState
          icon={FileCheck}
          title={statusFilter === "ALL" ? "No Tailored Resumes Yet" : `No Resumes with status "${statusFilter}"`}
          description={
            statusFilter === "ALL"
              ? "Discover qualified jobs in Job Discovery or review your high-affinity Job Matches to generate truthful, ATS-optimized tailored resumes."
              : "Try switching back to 'All' status filter to view all tailored resumes."
          }
          action={
            <Link to="/matches">
              <Button variant="primary" size="sm">
                <Sparkles className="w-3.5 h-3.5" />
                Explore Qualified Matches
              </Button>
            </Link>
          }
        />
      )}

      {!isLoading && !error && filteredItems.length > 0 && (
        <div className="space-y-4">
          <div className="space-y-3">
            {filteredItems.map((item) => (
              <TailoredResumeCard key={item.id} tailoredResume={item} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-terminal-warmBorder text-xs text-terminal-muted">
              <div>
                Page <span className="font-semibold text-terminal-dark">{page}</span> of{" "}
                <span className="font-semibold text-terminal-dark">{totalPages}</span> ({total} records)
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => handlePageChange(page - 1)}
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => handlePageChange(page + 1)}
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
