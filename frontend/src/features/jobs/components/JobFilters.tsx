import { useState, useEffect } from "react";
import { Search, X, RotateCcw } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export interface JobFiltersProps {
  search: string;
  workplaceType: string;
  status: string;
  onSearchChange: (value: string) => void;
  onWorkplaceTypeChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onReset: () => void;
}

export function JobFilters({
  search,
  workplaceType,
  status,
  onSearchChange,
  onWorkplaceTypeChange,
  onStatusChange,
  onReset,
}: JobFiltersProps) {
  const [localSearch, setLocalSearch] = useState(search);

  // Sync external search changes to local state
  useEffect(() => {
    setLocalSearch(search);
  }, [search]);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localSearch !== search) {
        onSearchChange(localSearch);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [localSearch, search, onSearchChange]);

  const hasActiveFilters = Boolean(search || workplaceType || status);

  return (
    <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle space-y-3">
      <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Input
            placeholder="Search by position title or company name..."
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            className="pl-9 pr-8 text-xs sm:text-sm font-sans"
            aria-label="Search jobs"
          />
          <Search className="w-4 h-4 text-terminal-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          {localSearch && (
            <button
              onClick={() => {
                setLocalSearch("");
                onSearchChange("");
              }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-terminal-muted hover:text-terminal-dark transition-colors"
              aria-label="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Dropdown Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="min-w-[130px]">
            <select
              value={workplaceType}
              onChange={(e) => onWorkplaceTypeChange(e.target.value)}
              className="w-full h-9 px-3 text-xs rounded-card border border-terminal-warmBorder bg-white text-terminal-dark font-sans focus:outline-none focus:ring-1 focus:ring-terminal-primary shadow-subtle"
              aria-label="Filter by workplace type"
            >
              <option value="">All Workplaces</option>
              <option value="REMOTE">Remote</option>
              <option value="HYBRID">Hybrid</option>
              <option value="ONSITE">On-site</option>
            </select>
          </div>

          <div className="min-w-[130px]">
            <select
              value={status}
              onChange={(e) => onStatusChange(e.target.value)}
              className="w-full h-9 px-3 text-xs rounded-card border border-terminal-warmBorder bg-white text-terminal-dark font-sans focus:outline-none focus:ring-1 focus:ring-terminal-primary shadow-subtle"
              aria-label="Filter by status"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="DISCOVERED">Discovered</option>
              <option value="EXPIRED">Expired</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>

          {hasActiveFilters && (
            <Button
              variant="outline"
              size="sm"
              onClick={onReset}
              className="h-9 px-3 text-xs gap-1.5 text-terminal-muted hover:text-terminal-dark border-dashed"
              title="Reset all filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
