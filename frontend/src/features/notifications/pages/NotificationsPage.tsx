import { useState, useMemo } from "react";
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Clock,
  Send,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/Button";
import { useNotifications } from "@/hooks/useNotifications";
import { NotificationsTable } from "../components/NotificationsTable";
import type { NotificationDeliveryStatus } from "@/types/notifications";

export function NotificationsPage() {
  const [currentPage, setCurrentPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<NotificationDeliveryStatus | undefined>(
    undefined
  );

  // Paginated query for table
  const {
    data: notificationsResponse,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useNotifications({
    status: statusFilter,
    page: currentPage,
    page_size: 10,
  });

  // Global KPI queries using server-side count totals (avoids pagination bias)
  const { data: totalAll } = useNotifications({ page: 1, page_size: 1 });
  const { data: totalSent } = useNotifications({ status: "SENT", page: 1, page_size: 1 });
  const { data: totalFailed } = useNotifications({ status: "FAILED", page: 1, page_size: 1 });
  const { data: totalPending } = useNotifications({ status: "PENDING", page: 1, page_size: 1 });
  const { data: totalProcessing } = useNotifications({
    status: "PROCESSING",
    page: 1,
    page_size: 1,
  });

  const totalDeliveries = totalAll?.pagination?.total_items ?? 0;
  const sentCount = totalSent?.pagination?.total_items ?? 0;
  const failedCount = totalFailed?.pagination?.total_items ?? 0;
  const inFlightCount =
    (totalPending?.pagination?.total_items ?? 0) +
    (totalProcessing?.pagination?.total_items ?? 0);

  const notifications = useMemo(
    () => notificationsResponse?.items || [],
    [notificationsResponse]
  );
  const pagination = notificationsResponse?.pagination;

  const filterTabs: Array<{ label: string; value?: NotificationDeliveryStatus; count?: number }> =
    [
      { label: "All Deliveries", value: undefined, count: totalDeliveries },
      { label: "Delivered", value: "SENT", count: sentCount },
      { label: "In Flight", value: "PROCESSING", count: inFlightCount },
      { label: "Failed", value: "FAILED", count: failedCount },
    ];

  const handleStatusChange = (val?: NotificationDeliveryStatus) => {
    setStatusFilter(val);
    setCurrentPage(1);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Email Notifications"
        description="Delivery tracking, PDF attachments, SMTP audit records, and retry operations"
        breadcrumbs={[{ label: "Notifications" }]}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="gap-1.5"
            title="Refresh deliveries"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>
        }
      />

      {/* KPI Overview Console */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">Total Deliveries</span>
            <Send className="w-4 h-4 text-terminal-muted" />
          </div>
          <div className="text-2xl font-bold font-mono text-terminal-dark">
            {totalDeliveries}
          </div>
          <span className="text-[11px] text-terminal-muted font-mono mt-1 block">
            Job match email dispatches
          </span>
        </div>

        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">Delivered (Sent)</span>
            <CheckCircle2 className="w-4 h-4 text-[#5BCB8A]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#1B5E20]">{sentCount}</div>
          <span className="text-[11px] text-[#2E7D32] font-mono mt-1 block">
            Confirmed SMTP transmission
          </span>
        </div>

        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">In Flight</span>
            <Clock className="w-4 h-4 text-[#E6B84D]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#6E4C00]">{inFlightCount}</div>
          <span className="text-[11px] text-terminal-muted font-mono mt-1 block">
            Pending or worker processing
          </span>
        </div>

        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">Delivery Failures</span>
            <AlertTriangle className="w-4 h-4 text-[#E05A47]" />
          </div>
          <div className="text-2xl font-bold font-mono text-terminal-errorText">
            {failedCount}
          </div>
          <span className="text-[11px] text-terminal-errorText font-mono mt-1 block">
            Eligible for manual retry
          </span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 pb-1 border-b border-terminal-warmBorder">
        {filterTabs.map((tab) => (
          <button
            key={tab.label}
            onClick={() => handleStatusChange(tab.value)}
            className={`px-3 py-1.5 rounded-card text-xs font-medium font-mono transition-colors flex items-center gap-1.5 ${
              statusFilter === tab.value
                ? "bg-terminal-dark text-white font-semibold shadow-subtle"
                : "text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] ${
                  statusFilter === tab.value
                    ? "bg-white/20 text-white"
                    : "bg-terminal-warm text-terminal-muted"
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <LoadingState message="Fetching notification delivery audit records..." />
      ) : error ? (
        <ErrorState
          title="Could not load notifications"
          message="Failed to retrieve delivery records from the backend. Please check your connection."
          onRetry={() => refetch()}
        />
      ) : notifications.length === 0 ? (
        <EmptyState
          icon={<Bell className="w-6 h-6 text-terminal-muted" />}
          title="No Notification Records Found"
          description={
            statusFilter
              ? `No notifications found with status '${statusFilter}'.`
              : "No email notifications have been dispatched yet. When pipeline runs discover qualified matches, delivery logs will appear here."
          }
        />
      ) : (
        <div className="space-y-4">
          <NotificationsTable notifications={notifications} onRefresh={() => refetch()} />

          {/* Pagination Controls */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between pt-2 text-xs font-mono text-terminal-muted">
              <span>
                Showing page {pagination.page} of {pagination.total_pages} ({pagination.total_items} total records)
              </span>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={!pagination.has_prev}
                  className="gap-1 h-8 px-2.5 text-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => p + 1)}
                  disabled={!pagination.has_next}
                  className="gap-1 h-8 px-2.5 text-xs"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
