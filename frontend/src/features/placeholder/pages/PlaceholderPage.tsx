import { LucideIcon, ArrowRight, Construction } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/Button";

export interface PlaceholderPageProps {
  title: string;
  description: string;
  icon: LucideIcon;
  targetMilestone: string;
  plannedFeatures: string[];
}

export function PlaceholderPage({
  title,
  description,
  icon: Icon,
  targetMilestone,
  plannedFeatures,
}: PlaceholderPageProps) {
  return (
    <div>
      <PageHeader
        title={title}
        description={description}
        breadcrumbs={[{ label: title }]}
      />

      <div className="max-w-2xl mx-auto mt-6 p-8 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-card text-center">
        <div className="w-14 h-14 mx-auto rounded-card bg-[#FF5A36]/10 border border-[#FF5A36]/30 flex items-center justify-center text-terminal-primary mb-4 shadow-subtle">
          <Icon className="w-7 h-7" />
        </div>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold font-mono bg-[#E6B84D]/15 text-[#6E4C00] border border-[#E6B84D]/40 mb-3">
          <Construction className="w-3.5 h-3.5" />
          Planned for {targetMilestone}
        </div>

        <h2 className="text-xl font-bold font-display text-terminal-dark mb-2">{title} Module</h2>
        <p className="text-sm text-terminal-muted mb-6 leading-relaxed font-sans">
          The backend API services for {title.toLowerCase()} are implemented and validated. The dedicated user interface will be connected in an upcoming milestone.
        </p>

        <div className="text-left bg-terminal-warm/60 border border-terminal-warmBorder/80 rounded-card p-5 mb-6">
          <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-3">
            Planned Frontend Capabilities:
          </h4>
          <ul className="space-y-2 text-xs text-terminal-dark">
            {plannedFeatures.map((feat) => (
              <li key={feat} className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-terminal-primary mt-1.5 shrink-0" />
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center justify-center gap-3">
          <Link to="/">
            <Button variant="outline" size="sm">
              Return to Dashboard
            </Button>
          </Link>
          <Link to="/pipeline">
            <Button variant="primary" size="sm" className="gap-1.5 shadow-subtle">
              <span>View Pipeline Runs</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

