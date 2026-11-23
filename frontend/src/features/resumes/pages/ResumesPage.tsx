import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Layers,
} from "lucide-react";
import { useResumes } from "@/hooks/useResumes";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ResumeCard } from "../components/ResumeCard";
import { ResumeUploadModal } from "../components/ResumeUploadModal";
import { formatDate, readPageParam } from "@/lib/utils";

const PAGE_SIZE = 10;

export function ResumesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const page = readPageParam(searchParams.get("page"));

  const { data: resumesResponse, isLoading, error, refetch } = useResumes({
    page,
    page_size: PAGE_SIZE,
  });

  const resumes = resumesResponse?.items || [];
  const total = resumesResponse?.pagination?.total_items || 0;
  const totalPages = resumesResponse?.pagination?.total_pages || Math.ceil(total / PAGE_SIZE) || 1;

  // Identify currently active resume
  const activeResume = resumes.find((r) => r.is_active);

  const handlePageChange = (newPage: number) => {
    const updated = new URLSearchParams(searchParams);
    updated.set("page", String(newPage));
    setSearchParams(updated);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Master Resumes"
        description="Upload and maintain your master candidate resumes, inspect parsed structured sections, and select active versions for truthful tailoring."
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Resumes" }]}
        actions={
          <div className="flex items-center gap-2">
            <Link to="/tailored-resumes">
              <Button variant="outline" size="sm">
                <Sparkles className="w-3.5 h-3.5 text-terminal-primary" />
                Tailored Resumes
              </Button>
            </Link>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsUploadModalOpen(true)}
            >
              <UploadCloud className="w-3.5 h-3.5" />
              Upload Resume
            </Button>
          </div>
        }
      />

      {isLoading && <LoadingState message="Loading master resumes and parsing status..." />}

      {error && (
        <ErrorState
          title="Failed to Load Resumes"
          message="Could not retrieve your uploaded master resumes. Please verify the backend connection and try again."
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !error && resumes.length === 0 && (
        <EmptyState
          icon={FileText}
          title="No Master Resumes Uploaded"
          description="Upload your primary resume in PDF or DOCX format. JobRadar AI will parse your work experience, skills, and projects, enabling truthful tailoring for qualified opportunities."
          actionLabel="Upload Your First Resume"
          onAction={() => setIsUploadModalOpen(true)}
        />
      )}

      {!isLoading && !error && resumes.length > 0 && (
        <div className="space-y-6">
          {/* Active Resume Callout Banner */}
          {activeResume && (
            <Card className="bg-[#D6FF3F]/10 border-[#B8E61A]/50">
              <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-card bg-[#D6FF3F]/30 border border-[#B8E61A]/60 flex items-center justify-center text-[#3B4D00]">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#3B4D00] font-mono">
                        Active Master Resume
                      </span>
                      <Badge variant="lime" className="text-[10px] py-0">
                        Primary Source
                      </Badge>
                    </div>
                    <p className="text-sm font-bold font-display text-terminal-dark mt-0.5">
                      {activeResume.original_filename}
                    </p>
                    <p className="text-xs text-terminal-muted font-mono">
                      Last updated: {formatDate(activeResume.updated_at)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Link to={`/resumes/${activeResume.id}`}>
                    <Button variant="outline" size="sm" className="bg-white/80">
                      View Parsed Data
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Master Resumes List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold font-display text-terminal-dark flex items-center gap-2">
                <Layers className="w-4 h-4 text-terminal-primary" />
                Uploaded Master Resumes ({total})
              </h2>
            </div>

            <div className="space-y-3">
              {resumes.map((resume) => (
                <ResumeCard
                  key={resume.id}
                  resume={resume}
                  onActivateSuccess={() => refetch()}
                />
              ))}
            </div>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-terminal-warmBorder text-xs text-terminal-muted">
              <div>
                Showing page <span className="font-semibold text-terminal-dark">{page}</span> of{" "}
                <span className="font-semibold text-terminal-dark">{totalPages}</span> ({total} resumes)
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

      {/* Upload Modal */}
      <ResumeUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={() => {
          refetch();
        }}
      />
    </div>
  );
}
