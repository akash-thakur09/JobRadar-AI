import { useState, useEffect } from "react";
import { Download, ExternalLink, FileText, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { tailoredResumesService } from "@/services/tailored-resumes.service";
import { triggerBlobDownload } from "@/lib/utils";
import type { TailoredResumeStatus } from "@/types/tailored-resumes";

interface PdfPreviewViewerProps {
  tailoredResumeId: string;
  fileName?: string | null;
  status: TailoredResumeStatus;
}

export function PdfPreviewViewer({
  tailoredResumeId,
  fileName,
  status,
}: PdfPreviewViewerProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [blobData, setBlobData] = useState<Blob | null>(null);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let createdUrl: string | null = null;

    if (status === "COMPLETED" && tailoredResumeId) {
      setIsLoadingPdf(true);
      setPdfError(null);

      tailoredResumesService
        .downloadTailoredPdf(tailoredResumeId)
        .then(({ data }) => {
          if (!active) return;
          setBlobData(data);
          createdUrl = URL.createObjectURL(data);
          setBlobUrl(createdUrl);
        })
        .catch((err) => {
          if (!active) return;
          console.error("Failed to load PDF preview:", err);
          setPdfError("Could not retrieve PDF binary for preview.");
        })
        .finally(() => {
          if (active) {
            setIsLoadingPdf(false);
          }
        });
    } else {
      setBlobUrl(null);
      setBlobData(null);
    }

    return () => {
      active = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [tailoredResumeId, status]);

  const handleDownload = () => {
    if (!blobData) return;
    const downloadName = fileName || `tailored-resume-${tailoredResumeId.substring(0, 8)}.pdf`;
    triggerBlobDownload(blobData, downloadName);
  };

  const handleOpenNewTab = () => {
    if (!blobUrl) return;
    window.open(blobUrl, "_blank");
  };

  if (status !== "COMPLETED") {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-terminal-warm/30 rounded-card border-2 border-dashed border-terminal-warmBorder min-h-[450px] text-center">
        {status === "FAILED" ? (
          <>
            <div className="w-12 h-12 rounded-full bg-terminal-error/15 text-terminal-error flex items-center justify-center mb-3">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h4 className="text-base font-bold font-display text-terminal-dark">PDF Generation Failed</h4>
            <p className="text-xs text-terminal-muted max-w-sm mt-1">
              The truthful tailoring pipeline failed to produce an ATS-compliant PDF document. Review claim validation details.
            </p>
          </>
        ) : (
          <>
            <div className="w-12 h-12 rounded-full bg-terminal-primary/10 text-terminal-primary flex items-center justify-center mb-3">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
            <h4 className="text-base font-bold font-display text-terminal-dark">Rendering ATS PDF</h4>
            <p className="text-xs text-terminal-muted max-w-sm mt-1">
              Current stage: <span className="font-mono font-semibold uppercase text-terminal-primary">{status}</span>. Compiling layout and typesetting...
            </p>
          </>
        )}
      </div>
    );
  }

  if (isLoadingPdf) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-terminal-warm/40 rounded-card border border-terminal-warmBorder min-h-[500px]">
        <Loader2 className="w-8 h-8 animate-spin text-terminal-primary mb-3" />
        <p className="text-xs font-mono text-terminal-muted">Fetching compiled PDF document...</p>
      </div>
    );
  }

  if (pdfError) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-terminal-warm rounded-card border border-terminal-warmBorder min-h-[300px] text-center">
        <AlertCircle className="w-8 h-8 text-terminal-error mb-2" />
        <p className="text-sm font-semibold text-terminal-dark">{pdfError}</p>
        <p className="text-xs text-terminal-muted mt-1">Please try downloading directly or refreshing.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Control bar */}
      <div className="flex items-center justify-between p-2.5 bg-terminal-warm rounded-card border border-terminal-warmBorder">
        <div className="flex items-center gap-2 text-xs font-mono text-terminal-dark">
          <FileText className="w-4 h-4 text-terminal-primary" />
          <span className="truncate max-w-[280px]">
            {fileName || `tailored-resume-${tailoredResumeId.substring(0, 8)}.pdf`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleOpenNewTab} disabled={!blobUrl}>
            <ExternalLink className="w-3.5 h-3.5" />
            New Tab
          </Button>
          <Button variant="primary" size="sm" onClick={handleDownload} disabled={!blobData}>
            <Download className="w-3.5 h-3.5" />
            Download PDF
          </Button>
        </div>
      </div>

      {/* PDF View Frame */}
      {blobUrl && (
        <div className="w-full bg-white rounded-card border border-terminal-warmBorder shadow-card overflow-hidden">
          <iframe
            src={blobUrl}
            title="Tailored Resume PDF Preview"
            className="w-full h-[700px] border-none"
          />
        </div>
      )}
    </div>
  );
}

