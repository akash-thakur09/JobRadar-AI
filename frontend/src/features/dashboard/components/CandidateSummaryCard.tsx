import { Link } from "react-router-dom";
import { ArrowRight, Briefcase, Calendar, MapPin, User, Award } from "lucide-react";
import type { CandidateProfile } from "@/types/candidate";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { formatExperience } from "@/lib/utils";

export interface CandidateSummaryCardProps {
  profile: CandidateProfile | null | undefined;
  skillsCount?: number;
}

export function CandidateSummaryCard({ profile, skillsCount = 0 }: CandidateSummaryCardProps) {
  if (!profile) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Active Candidate</CardTitle>
          <CardDescription>Target credentials for matching & tailoring</CardDescription>
        </CardHeader>
        <CardContent className="text-center py-6">
          <div className="w-10 h-10 rounded-full bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-muted mx-auto mb-2">
            <User className="w-5 h-5" />
          </div>
          <p className="text-xs text-terminal-muted mb-3 font-mono">No active candidate profile detected.</p>
          <Link to="/profile">
            <Button variant="outline" size="sm">Create Profile</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <User className="w-4 h-4 text-terminal-primary" />
            <span>Candidate Profile</span>
          </CardTitle>
          <CardDescription>Verified profile for AI matching</CardDescription>
        </div>
        <Link to="/profile">
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1 text-terminal-primary hover:text-terminal-primaryHover">
            <span>Manage</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </Link>
      </CardHeader>

      <CardContent className="space-y-4 flex-1">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-full bg-terminal-warm text-terminal-primary flex items-center justify-center font-bold font-display text-base shrink-0 border border-terminal-warmBorder shadow-subtle">
            {profile.full_name ? profile.full_name.charAt(0).toUpperCase() : "C"}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <h4 className="text-sm font-bold font-display text-terminal-dark truncate">{profile.full_name}</h4>
              <Badge variant="brand" className="text-[10px] py-0 px-1.5">Active</Badge>
            </div>
            <p className="text-xs text-terminal-muted truncate mt-0.5">
              {profile.headline || profile.current_role || "Candidate"}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs pt-1">
          <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/80 flex items-center gap-2">
            <Briefcase className="w-3.5 h-3.5 text-terminal-muted shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-terminal-muted block uppercase font-mono font-bold">Role</span>
              <span className="text-terminal-dark font-medium truncate block">
                {profile.current_role || "Not set"}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/80 flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-terminal-muted shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-terminal-muted block uppercase font-mono font-bold">Experience</span>
              <span className="text-terminal-dark font-mono font-medium truncate block">
                {formatExperience(profile.total_experience_months)}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/80 flex items-center gap-2">
            <MapPin className="w-3.5 h-3.5 text-terminal-muted shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-terminal-muted block uppercase font-mono font-bold">Location</span>
              <span className="text-terminal-dark font-medium truncate block">
                {profile.city || profile.country || "Remote"}
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/80 flex items-center gap-2">
            <Award className="w-3.5 h-3.5 text-terminal-muted shrink-0" />
            <div className="min-w-0">
              <span className="text-[10px] text-terminal-muted block uppercase font-mono font-bold">Skills Vault</span>
              <span className="text-terminal-dark font-mono font-medium truncate block">
                {skillsCount} Verified
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

