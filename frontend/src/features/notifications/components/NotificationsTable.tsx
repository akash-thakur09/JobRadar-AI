import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, RotateCw, FileCheck, ExternalLink, Mail } from "lucide-react";
import type { NotificationDeliverySummary } from "@/types/notifications";
import { NotificationStatusBadge } from "./NotificationStatusBadge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";
import { useRetryNotification } from "@/hooks/useNotifications";

export interface NotificationsTableProps {
  notifications: NotificationDeliverySummary[];
  onRefresh?: () => void;
}

export function NotificationsTable({ notifications }: NotificationsTableProps) {
  const navigate = useNavigate();
  const retryMutation = useRetryNotification();
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<{ id: string; message: string; isError?: boolean } | null>(null);

  const handleRetry = async (e: React.MouseEvent, notification: NotificationDeliverySummary) => {
    e.stopPropagation();
    if (retryingId) return; // Prevent duplicate submissions

    setActionNotice(null);
    setRetryingId(notification.id);

    try {
      const response = await retryMutation.mutateAsync({
        deliveryId: notification.id,
        payload: { force: notification.attempt_count >= notification.max_attempts },
      });
      setActionNotice({
        id: notification.id,
        message: `${response.message} (Status: ${response.status})`,
      });
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to trigger retry.";
      setActionNotice({
        id: notification.id,
        message: errMsg,
        isError: true,
      });
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <div className="space-y-3">
      {actionNotice && (
        <div
          className={`p-3 rounded-card text-xs font-mono flex items-center justify-between ${
            actionNotice.isError
              ? "bg-terminal-error/15 border border-terminal-error/40 text-terminal-errorText"
              : "bg-[#8DB4FF]/15 border border-[#8DB4FF]/40 text-[#0039A6]"
          }`}
        >
          <span>{actionNotice.message}</span>
          <button
            onClick={() => setActionNotice(null)}
            className="text-xs hover:underline ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="overflow-x-auto rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-card">
        <table className="w-full text-left text-xs text-terminal-dark">
          <thead className="bg-terminal-warm border-b border-terminal-warmBorder text-[10px] font-semibold text-terminal-muted uppercase font-mono tracking-wider">
            <tr>
              <th scope="col" className="px-4 py-3">Recipient</th>
              <th scope="col" className="px-4 py-3">Job & Match</th>
              <th scope="col" className="px-4 py-3">Tailored Resume</th>
              <th scope="col" className="px-4 py-3">Status</th>
              <th scope="col" className="px-4 py-3 text-center">Attempts</th>
              <th scope="col" className="px-4 py-3">Created</th>
              <th scope="col" className="px-4 py-3">Last Activity</th>
              <th scope="col" className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-terminal-warmBorder/60">
            {notifications.map((item) => {
              const isFailed = item.status === "FAILED";
              const isRetrying = retryingId === item.id;
              const lastActivity = item.sent_at || item.failed_at;

              return (
                <tr
                  key={item.id}
                  onClick={() => navigate(`/notifications/${item.id}`)}
                  className="hover:bg-terminal-warm/60 cursor-pointer transition-colors"
                >
                  {/* Recipient */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 font-medium text-terminal-dark">
                      <Mail className="w-3.5 h-3.5 text-terminal-muted shrink-0" />
                      <span className="truncate max-w-[200px]" title={item.recipient_email}>
                        {item.recipient_email}
                      </span>
                    </div>
                    <span className="text-[10px] text-terminal-muted font-mono block">
                      Provider: {item.provider}
                    </span>
                  </td>

                  {/* Related Job */}
                  <td className="px-4 py-3">
                    {item.job_title ? (
                      <div>
                        <Link
                          to={`/jobs/${item.job_id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-medium text-terminal-dark hover:text-terminal-primary hover:underline line-clamp-1"
                        >
                          {item.job_title}
                        </Link>
                        <span className="text-[11px] text-terminal-muted block">
                          {item.company_name || "Target Opportunity"}
                        </span>
                      </div>
                    ) : (
                      <Link
                        to={`/jobs/${item.job_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="font-mono text-terminal-muted hover:text-terminal-dark flex items-center gap-1"
                      >
                        <span>Job ID: {item.job_id.slice(0, 8)}...</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    )}
                  </td>

                  {/* Related Tailored Resume */}
                  <td className="px-4 py-3">
                    <Link
                      to={`/tailored-resumes/${item.tailored_resume_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-terminal-dark hover:text-terminal-primary hover:underline font-mono text-xs"
                      title="Inspect Tailored PDF Resume"
                    >
                      <FileCheck className="w-3.5 h-3.5 text-[#5BCB8A] shrink-0" />
                      <span>{item.tailored_resume_id.slice(0, 8)}...</span>
                    </Link>
                  </td>

                  {/* Delivery Status */}
                  <td className="px-4 py-3">
                    <NotificationStatusBadge status={item.status} />
                  </td>

                  {/* Attempts */}
                  <td className="px-4 py-3 text-center font-mono">
                    <span
                      className={`px-2 py-0.5 rounded font-mono font-semibold text-xs ${
                        isFailed
                          ? "bg-terminal-error/15 text-terminal-errorText"
                          : "text-terminal-dark"
                      }`}
                    >
                      {item.attempt_count} / {item.max_attempts}
                    </span>
                  </td>

                  {/* Created At */}
                  <td className="px-4 py-3 text-terminal-muted font-mono whitespace-nowrap">
                    {formatDate(item.created_at)}
                  </td>

                  {/* Last Activity */}
                  <td className="px-4 py-3 text-terminal-muted font-mono whitespace-nowrap">
                    {lastActivity ? formatDate(lastActivity) : "—"}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <div
                      className="flex items-center justify-end gap-1.5"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/notifications/${item.id}`)}
                        className="h-7 px-2 text-xs"
                        title="View Notification Details"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1 text-terminal-muted" />
                        <span>Inspect</span>
                      </Button>

                      {isFailed && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => handleRetry(e, item)}
                          disabled={isRetrying}
                          className="h-7 px-2 text-xs gap-1 border-terminal-error/40 text-terminal-errorText hover:bg-terminal-error/10"
                          title="Retry failed email transmission"
                        >
                          <RotateCw
                            className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`}
                          />
                          <span>{isRetrying ? "Retrying..." : "Retry"}</span>
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

