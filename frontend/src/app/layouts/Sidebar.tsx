import { NavLink } from "react-router-dom";
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  FileText,
  Globe,
  LayoutDashboard,
  PlayCircle,
  Radar,
  Settings,
  Sparkles,
  User,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui.store";
import { useCandidateProfile } from "@/hooks/useCandidateProfile";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  isPlaceholder?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Candidate Profile", href: "/profile", icon: User },
  { label: "Job Discovery", href: "/jobs", icon: Globe },
  { label: "Job Matches", href: "/matches", icon: Sparkles },
  { label: "Resumes", href: "/resumes", icon: FileText, isPlaceholder: true },
  { label: "Notifications", href: "/notifications", icon: Bell, isPlaceholder: true },
  { label: "Pipeline Runs", href: "/pipeline", icon: PlayCircle },
  { label: "Settings", href: "/settings", icon: Settings, isPlaceholder: true },
];

export function Sidebar() {
  const {
    isDesktopSidebarCollapsed,
    isMobileSidebarOpen,
    toggleDesktopSidebar,
    setMobileSidebarOpen,
  } = useUIStore();

  const { data: profile } = useCandidateProfile();

  const handleNavClick = () => {
    if (isMobileSidebarOpen) {
      setMobileSidebarOpen(false);
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileSidebarOpen && (
        <div
          role="presentation"
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-terminal-dark/70 backdrop-blur-xs lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 z-50 flex flex-col bg-terminal-dark text-white transition-all duration-300 ease-in-out border-r border-terminal-secondary",
          isDesktopSidebarCollapsed ? "w-20" : "w-64",
          isMobileSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Brand Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-terminal-secondary shrink-0">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-card bg-terminal-primary flex items-center justify-center shrink-0 shadow-subtle">
              <Radar className="w-5 h-5 text-white animate-pulse" />
            </div>
            {!isDesktopSidebarCollapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-sm tracking-tight text-white flex items-center gap-1.5 font-display">
                  JobRadar AI
                  <span className="text-[10px] uppercase font-semibold font-mono px-1.5 py-0.2 bg-terminal-elevated text-terminal-muted rounded border border-terminal-elevated">
                    v1.0
                  </span>
                </span>
                <span className="text-[11px] text-terminal-muted font-sans">Intelligence Terminal</span>
              </div>
            )}
          </div>

          {/* Close Mobile Drawer */}
          <button
            onClick={() => setMobileSidebarOpen(false)}
            className="lg:hidden p-1.5 rounded-md text-terminal-muted hover:text-white hover:bg-terminal-secondary"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={handleNavClick}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-card text-xs font-medium transition-all group relative",
                    isActive
                      ? "bg-terminal-secondary text-white shadow-subtle font-semibold border-l-2 border-terminal-primary"
                      : "text-terminal-muted hover:bg-terminal-secondary/60 hover:text-white",
                    isDesktopSidebarCollapsed && "justify-center px-2"
                  )
                }
                title={isDesktopSidebarCollapsed ? item.label : undefined}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!isDesktopSidebarCollapsed && (
                  <span className="flex-1 truncate">{item.label}</span>
                )}
                {!isDesktopSidebarCollapsed && item.isPlaceholder && (
                  <span className="text-[9px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded bg-terminal-secondary text-terminal-muted border border-terminal-elevated">
                    Soon
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Candidate Profile Widget at Bottom */}
        <div className="p-3 border-t border-terminal-secondary shrink-0">
          <div
            className={cn(
              "flex items-center gap-3 p-2 rounded-card bg-terminal-secondary/60 border border-terminal-elevated/40",
              isDesktopSidebarCollapsed ? "justify-center p-1.5" : ""
            )}
          >
            <div className="w-8 h-8 rounded-full bg-terminal-elevated flex items-center justify-center text-terminal-warm font-semibold text-xs shrink-0 font-display">
              {profile?.full_name ? profile.full_name.charAt(0).toUpperCase() : "U"}
            </div>
            {!isDesktopSidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate font-display">
                  {profile?.full_name || "Active Candidate"}
                </p>
                <p className="text-[10px] text-terminal-muted truncate font-mono">
                  {profile?.headline || profile?.current_role || "Profile Configured"}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Desktop Collapse Toggle */}
        <div className="hidden lg:flex items-center justify-center p-2 border-t border-terminal-secondary">
          <button
            onClick={toggleDesktopSidebar}
            className="w-full flex items-center justify-center gap-2 p-1.5 rounded-md text-terminal-muted hover:text-white hover:bg-terminal-secondary text-xs font-medium transition-colors"
            title={isDesktopSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label="Toggle sidebar collapse"
          >
            {isDesktopSidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span>Collapse Sidebar</span>
              </>
            )}
          </button>
        </div>
      </aside>
    </>
  );
}
