import { Link } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center text-xs text-terminal-muted mb-2 font-mono">
      <Link to="/" className="hover:text-terminal-dark transition-colors flex items-center">
        <Home className="w-3.5 h-3.5" />
        <span className="sr-only">Dashboard</span>
      </Link>
      {items.map((item, index) => (
        <span key={item.label} className="flex items-center">
          <ChevronRight className="w-3 h-3 mx-1.5 text-terminal-muted/60 shrink-0" />
          {item.href && index < items.length - 1 ? (
            <Link to={item.href} className="hover:text-terminal-dark transition-colors">
              {item.label}
            </Link>
          ) : (
            <span className="text-terminal-dark font-medium">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

