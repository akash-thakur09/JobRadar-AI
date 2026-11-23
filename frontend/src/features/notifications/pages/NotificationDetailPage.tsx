import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  RotateCw,
  AlertTriangle,
  FileCheck,
  Briefcase,
  Sparkles,
  Server,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { NotificationStatusBadge } from "../components/NotificationStatusBadge";
import { useNotification, useRetryNotification } from "@/hooks/useNotifications";
import { formatDate } from "@/lib/utils";

export function NotificationDetailPage() {
  const { notificationId = "" } = useParams<{ notificationId: string }>();

  const {
    data: notification,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useNotification(notificationId);

  const retryMutation = useRetryNotification();
  const [forceRetry, setForceRetry] = useState(false);
  const [retryNotice, setRetryNotice] = useState<{ message: string; isError?: boolean } | null>(
    null
  );

  const isFailed = notification?.status === "FAILED";
  const isRetrying = retryMutation.isPending;
  const isMaxAttemptsExceeded =
    notification && notification.attempt_count >= notification.max_attempts;

  const handleRetry = async () => {
    if (!notification || isRetrying) return;
    setRetryNotice(null);

    try {
      const response = await retryMutation.mutateAsync({
        deliveryId: notification.id,
        payload: { force: forceRetry || isMaxAttemptsExceeded },
      });
      setRetryNotice({
        message: `${response.message} (Status: ${response.status})`,
      });
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to retry notification delivery.";
      setRetryNotice({
        message: errMsg,
        isError: true,
      });
    }
  };

  if (isLoading) {
    return <LoadingState message="Loading notification audit details..." />;
  }

  if (error || !notification) {
    return (
      <ErrorState
        title="Notification Not Found"
        message="Unable to locate the specified notification delivery record."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notification Delivery Audit"
        description="Comprehensive lifecycle telemetry, SMTP verification, and error diagnostics"
        breadcrumbs={[
          { label: "Notifications", href: "/notifications" },
          { label: `${notification.id.slice(0, 8)}...` },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="gap-1.5"
              title="Refresh record"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </Button>

            {isFailed && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleRetry}
                disabled={isRetrying}
                className="gap-1.5 shadow-xs"
              >
                <RotateCw className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`} />
                <span>{isRetrying ? "Scheduling Retry..." : "Retry Delivery"}</span>
              </Button>
            )}
          </div>
        }
      />

      {/* Action Notice */}
      {retryNotice && (
        <Alert variant={retryNotice.isError ? "error" : "info"}>
          <div className="flex items-center justify-between">
            <span>{retryNotice.message}</span>
            <button
              onClick={() => setRetryNotice(null)}
              className="text-xs hover:underline ml-4"
            >
              Dismiss
            </button>
          </div>
        </Alert>
      )}

      {/* Hero Overview Card */}
      <div className="p-5 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-terminal-warmBorder">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-lg font-bold font-display text-terminal-dark">
                {notification.recipient_email}
              </h2>
              <NotificationStatusBadge status={notification.status} />
            </div>
            <p className="text-xs text-terminal-muted font-mono mt-0.5">
              Delivery UUID: {notification.id}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block">
                Attempts
              </span>
              <span className="font-mono font-bold text-sm text-terminal-dark">
                {notification.attempt_count} / {notification.max_attempts}
              </span>
            </div>
          </div>
        </div>

        {/* Key Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 text-xs">
          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Notification Type
            </span>
            <span className="font-mono font-medium text-terminal-dark">
              {notification.notification_type}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Provider
            </span>
            <div className="flex items-center gap-1 font-mono font-medium text-terminal-dark">
              <Server className="w-3.5 h-3.5 text-terminal-muted" />
              <span>{notification.provider.toUpperCase()}</span>
            </div>
          </div>

          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Created Timestamp
            </span>
            <span className="font-mono text-terminal-dark">
              {formatDate(notification.created_at)}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Last Updated
            </span>
            <span className="font-mono text-terminal-dark">
              {formatDate(notification.updated_at)}
            </span>
          </div>
        </div>
      </div>

      {/* Failure Diagnostics Card */}
      {isFailed && (
        <div className="p-5 rounded-card border border-terminal-error/40 bg-terminal-error/5 shadow-subtle space-y-3">
          <div className="flex items-center gap-2 text-terminal-errorText font-semibold font-display text-sm">
            <AlertTriangle className="w-4 h-4 text-terminal-errorText" />
            <span>Delivery Failure Diagnostics</span>
          </div>

          <div className="p-3.5 rounded-card bg-terminal-error/10 border border-terminal-error/20 font-mono text-xs text-terminal-errorText whitespace-pre-wrap">
            {notification.last_error || "No explicit error details reported by SMTP transport."}
          </div>

          {notification.failed_at && (
            <p className="text-xs text-terminal-muted font-mono">
              Failed At: {formatDate(notification.failed_at)}
            </p>
          )}

          {/* Retry Controls */}
          <div className="pt-2 border-t border-terminal-error/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              {isMaxAttemptsExceeded && (
                <label className="flex items-center gap-2 text-xs font-mono text-terminal-dark cursor-pointer">
                  <input
                    type="checkbox"
                    checked={forceRetry}
                    onChange={(e) => setForceRetry(e.target.checked)}
                    className="rounded border-terminal-warmBorder text-terminal-primary focus:ring-terminal-primary"
                  />
                  <span>Force retry (override maximum attempt limit of {notification.max_attempts})</span>
                </label>
              )}
            </div>

            <Button
              variant="danger"
              size="sm"
              onClick={handleRetry}
              disabled={isRetrying}
              className="gap-1.5 text-xs shadow-xs"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`} />
              <span>{isRetrying ? "Scheduling Retry..." : "Trigger Manual Retry"}</span>
            </Button>
          </div>

          <p className="text-[11px] text-terminal-muted font-mono italic">
            Notice: Triggering retry sets the status to PENDING and enqueues the task with the Celery background worker. Delivery confirmation is updated once the SMTP server accepts the message.
          </p>
        </div>
      )}

      {/* SMTP Message ID & Sent Confirmation */}
      {notification.status === "SENT" && (
        <div className="p-4 rounded-card border border-[#5BCB8A]/40 bg-[#5BCB8A]/10 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-[#2E7D32] shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <span className="font-semibold text-[#1B5E20] font-display block">
              SMTP Transmission Successfully Acknowledged
            </span>
            <p className="text-terminal-dark font-mono">
              Delivered at: {notification.sent_at ? formatDate(notification.sent_at) : "Confirmed"}
            </p>
            {notification.provider_message_id && (
              <p className="text-terminal-muted font-mono text-[11px]">
                SMTP Message-ID: <span className="text-terminal-dark">{notification.provider_message_id}</span>
              </p>
            )}
          </div>
        </div>
      )}

      {/* Related Resources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Target Job */}
        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold font-display text-terminal-dark">
            <Briefcase className="w-4 h-4 text-terminal-primary" />
            <span>Target Job Opportunity</span>
          </div>

          {notification.job_title ? (
            <div className="space-y-1">
              <h4 className="font-bold text-sm text-terminal-dark line-clamp-1">
                {notification.job_title}
              </h4>
              <p className="text-xs text-terminal-muted">
                {notification.company_name || "Company Details"}
              </p>
            </div>
          ) : (
            <span className="text-xs text-terminal-muted font-mono">
              Job UUID: {notification.job_id}
            </span>
          )}

          <div className="mt-3 pt-3 border-t border-terminal-warmBorder">
            <Link
              to={`/jobs/${notification.job_id}`}
              className="inline-flex items-center gap-1 text-xs text-terminal-primary font-medium hover:underline"
            >
              <span>View Job Details</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        {/* Evaluated Match */}
        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold font-display text-terminal-dark">
            <Sparkles className="w-4 h-4 text-[#8DB4FF]" />
            <span>Candidate Job Match</span>
          </div>

          <div className="space-y-1">
            {notification.match_score !== null && notification.match_score !== undefined ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-terminal-muted font-mono">Final Score:</span>
                <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-[#D6FF3F]/30 text-[#3B4D00]">
                  {Math.round(notification.match_score)}%
                </span>
              </div>
            ) : (
              <span className="text-xs text-terminal-muted font-mono">
                Match UUID: {notification.job_match_id}
              </span>
            )}
            <p className="text-xs text-terminal-muted font-mono">
              Matched against active candidate profile
            </p>
          </div>

          <div className="mt-3 pt-3 border-t border-terminal-warmBorder">
            <Link
              to={`/matches/${notification.job_match_id}`}
              className="inline-flex items-center gap-1 text-xs text-terminal-primary font-medium hover:underline"
            >
              <span>View Match Breakdown</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        {/* Tailored Resume */}
        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold font-display text-terminal-dark">
            <FileCheck className="w-4 h-4 text-[#5BCB8A]" />
            <span>Attached Tailored PDF</span>
          </div>

          <div className="space-y-1">
            <span className="text-xs font-mono text-terminal-dark block truncate">
              ID: {notification.tailored_resume_id}
            </span>
            <p className="text-xs text-terminal-muted">
              ATS-optimized document tailored to job requirements
            </p>
          </div>

          <div className="mt-3 pt-3 border-t border-terminal-warmBorder">
            <Link
              to={`/tailored-resumes/${notification.tailored_resume_id}`}
              className="inline-flex items-center gap-1 text-xs text-terminal-primary font-medium hover:underline"
            >
              <span>Inspect Tailored Resume</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
