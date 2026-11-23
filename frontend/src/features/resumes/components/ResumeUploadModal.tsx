import { useEffect, useState, useRef, type DragEvent, type ChangeEvent, type KeyboardEvent } from "react";
import { UploadCloud, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { useUploadResume } from "@/hooks/useResumes";
import { extractErrorMessage, formatBytes } from "@/lib/utils";
import type { MasterResumeDetailResponse } from "@/types/resumes";

interface ResumeUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (resume: MasterResumeDetailResponse) => void;
}

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const ALLOWED_MIME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
];

export function ResumeUploadModal({ isOpen, onClose, onSuccess }: ResumeUploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const browseRef = useRef<HTMLButtonElement>(null);

  const uploadMutation = useUploadResume();

  useEffect(() => {
    if (!isOpen) return;
    const previousFocus = document.activeElement;
    browseRef.current?.focus();
    return () => {
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
        previousFocus.focus();
      }
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const validateFile = (file: File): string | null => {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext) && !ALLOWED_MIME_TYPES.includes(file.type)) {
      return "Only PDF and DOCX files are supported.";
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File size exceeds the 10MB limit (selected: ${formatBytes(file.size)}).`;
    }
    if (file.size === 0) {
      return "File is empty (0 bytes). Please select a valid resume file.";
    }
    return null;
  };

  const handleFileSelection = (file: File) => {
    setValidationError(null);
    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelection(file);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelection(file);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setValidationError(null);
    uploadMutation.reset();
    onClose();
  };

  const handleDialogKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && !uploadMutation.isPending) {
      event.preventDefault();
      handleClose();
    }
    if (event.key !== "Tab") return;

    const focusable = dialogRef.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
    if (!focusable?.length) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;
    try {
      const result = await uploadMutation.mutateAsync(selectedFile);
      if (onSuccess) {
        onSuccess(result);
      }
      handleClose();
    } catch {
      // Error handled by uploadMutation.error
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-terminal-dark/70 backdrop-blur-xs p-4">
      <div
        ref={dialogRef}
        className="w-full max-w-lg bg-terminal-warmSurface border border-terminal-warmBorder rounded-card shadow-2xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
        onKeyDown={handleDialogKeyDown}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-terminal-warmBorder">
          <div>
            <h2 id="upload-modal-title" className="text-lg font-bold font-display text-terminal-dark">
              Upload Master Resume
            </h2>
            <p className="text-xs text-terminal-muted mt-0.5">
              Upload your canonical resume in PDF or DOCX format for parsing and tailoring.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={uploadMutation.isPending}
            className="p-1 rounded text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Drag & Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-card p-6 flex flex-col items-center justify-center transition-colors ${
              isDragOver
                ? "border-terminal-primary bg-terminal-primary/5"
                : "border-terminal-warmBorder hover:border-terminal-muted bg-terminal-warm/30"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="hidden"
              onChange={handleInputChange}
            />
            <div className="w-12 h-12 rounded-full bg-terminal-warm flex items-center justify-center text-terminal-muted mb-3 border border-terminal-warmBorder">
              <UploadCloud className="w-6 h-6 text-terminal-primary" />
            </div>
            <Button
              ref={browseRef}
              type="button"
              variant="outline"
              size="sm"
              disabled={uploadMutation.isPending}
              onClick={() => fileInputRef.current?.click()}
            >
              Browse files
            </Button>
            <p className="text-xs text-terminal-muted mt-1 font-mono">
              Or drop a PDF or DOCX file up to 10 MB.
            </p>
          </div>

          {/* Selected File Details */}
          {selectedFile && (
            <div className="flex items-center justify-between p-3.5 bg-terminal-warm rounded-card border border-terminal-warmBorder">
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="w-8 h-8 rounded bg-terminal-warmSurface border border-terminal-warmBorder flex items-center justify-center shrink-0">
                  <FileText className="w-4 h-4 text-terminal-primary" />
                </div>
                <div className="truncate">
                  <p className="text-xs font-semibold text-terminal-dark truncate">{selectedFile.name}</p>
                  <p className="text-[11px] text-terminal-muted font-mono">{formatBytes(selectedFile.size)}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
                className="text-xs text-terminal-muted hover:text-terminal-error p-1"
                aria-label="Remove selected file"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Client-side Validation Error */}
          {validationError && (
            <Alert variant="error" title="Validation Error">
              {validationError}
            </Alert>
          )}

          {/* Backend Error Alert */}
          {uploadMutation.isError && (
            <Alert variant="error" title="Upload Failed">
              {extractErrorMessage(uploadMutation.error, "Failed to upload and parse resume file.")}
            </Alert>
          )}

          {/* Upload Success Alert */}
          {uploadMutation.isSuccess && (
            <Alert variant="success" title="Upload Complete">
              Master resume uploaded and parsed successfully.
            </Alert>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 bg-terminal-warm/50 border-t border-terminal-warmBorder">
          <Button variant="outline" size="sm" onClick={handleClose} disabled={uploadMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!selectedFile || uploadMutation.isPending}
            isLoading={uploadMutation.isPending}
            onClick={handleSubmit}
          >
            Upload Resume
          </Button>
        </div>
      </div>
    </div>
  );
}
