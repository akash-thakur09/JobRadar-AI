import { useState } from "react";
import { Filter, Sliders, Target, Clock, MapPin, Building2, Edit3, CheckCircle2 } from "lucide-react";
import type { CandidatePreferences } from "@/types/candidate";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { PreferencesEditForm } from "./PreferencesEditForm";

export interface PreferencesCardProps {
  preferences: CandidatePreferences;
}

export function PreferencesCard({ preferences }: PreferencesCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [showSuccessToast, setShowSuccessToast] = useState(false);

  const minScore = Number(preferences.minimum_relevance_score) || 0;

  const handleUpdateSuccess = () => {
    setIsEditing(false);
    setShowSuccessToast(true);
    setTimeout(() => setShowSuccessToast(false), 4000);
  };

  return (
    <Card className="relative overflow-hidden">
      {showSuccessToast && (
        <div className="absolute top-3 right-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-card bg-terminal-success text-[#185C36] text-xs font-medium border border-terminal-success/40 shadow-dropdown transition-all animate-bounce">
          <CheckCircle2 className="w-4 h-4" />
          <span>Preferences updated successfully!</span>
        </div>
      )}

      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-terminal-primary" />
            <span>Job Matching Preferences</span>
          </CardTitle>
          <CardDescription>
            Deterministic scoring rules and eligibility filters applied to incoming jobs
          </CardDescription>
        </div>
        {!isEditing && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(true)}
            className="gap-1.5 text-xs shrink-0"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit Preferences</span>
          </Button>
        )}
      </CardHeader>

      <CardContent>
        {isEditing ? (
          <PreferencesEditForm
            preferences={preferences}
            onSuccess={handleUpdateSuccess}
            onCancel={() => setIsEditing(false)}
          />
        ) : (
          <div className="space-y-5">
            {/* Min score badge & max age */}
            <div className="flex flex-wrap items-center gap-4 p-3 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-terminal-primary" />
                <span className="text-xs text-terminal-muted font-medium font-sans">Min Match Score:</span>
                <span className="font-bold text-sm font-mono text-terminal-dark px-2 py-0.5 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder">
                  {minScore.toFixed(0)}%
                </span>
              </div>

              <div className="h-4 w-px bg-terminal-warmBorder hidden sm:block" />

              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-terminal-muted" />
                <span className="text-xs text-terminal-muted font-medium font-sans">Max Job Age:</span>
                <span className="text-xs font-semibold font-mono text-terminal-dark">
                  {preferences.max_job_age_days} days
                </span>
              </div>
            </div>

            {/* Preferred Titles */}
            <div>
              <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2 flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-terminal-muted" />
                Target Job Titles
              </h4>
              {preferences.preferred_titles && preferences.preferred_titles.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {preferences.preferred_titles.map((title) => (
                    <Badge key={title} variant="brand">
                      {title}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs italic text-terminal-muted font-mono">No specific titles restricted.</p>
              )}
            </div>

            {/* Workplace & Employment Types */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2 flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-terminal-muted" />
                  Workplace Types
                </h4>
                {preferences.preferred_workplace_types && preferences.preferred_workplace_types.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {preferences.preferred_workplace_types.map((wt) => (
                      <Badge key={wt} variant="neutral">
                        {wt}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs italic text-terminal-muted font-mono">Any workplace arrangement.</p>
                )}
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-terminal-muted" />
                  Employment Types
                </h4>
                {preferences.preferred_employment_types && preferences.preferred_employment_types.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {preferences.preferred_employment_types.map((et) => (
                      <Badge key={et} variant="neutral">
                        {et.replace("_", " ")}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs italic text-terminal-muted font-mono">Any employment type.</p>
                )}
              </div>
            </div>

            {/* Preferred Locations */}
            <div>
              <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-terminal-muted" />
                Target Locations
              </h4>
              {preferences.preferred_locations && preferences.preferred_locations.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {preferences.preferred_locations.map((loc) => (
                    <Badge key={loc} variant="neutral">
                      {loc}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs italic text-terminal-muted font-mono">No target locations restricted.</p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
