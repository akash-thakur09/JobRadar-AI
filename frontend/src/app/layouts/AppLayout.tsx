import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useUIStore } from "@/stores/ui.store";
import { cn } from "@/lib/utils";

export function AppLayout() {
  const { isDesktopSidebarCollapsed } = useUIStore();

  return (
    <div className="min-h-screen bg-terminal-warm text-terminal-dark flex flex-col font-sans">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Workspace Frame */}
      <div
        className={cn(
          "flex-1 flex flex-col transition-all duration-300 ease-in-out",
          isDesktopSidebarCollapsed ? "lg:pl-20" : "lg:pl-64"
        )}
      >
        <Header />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

