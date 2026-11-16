import { useState } from "react";
import { Briefcase, Calendar, CheckCircle2, Edit3, Globe, MapPin, ShieldCheck, User } from "lucide-react";
import type { CandidateProfile } from "@/types/candidate";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { formatDate, formatExperience } from "@/lib/utils";
import { ProfileEditForm } from "./ProfileEditForm";

export interface ProfileCardProps {
  profile: CandidateProfile;
}

export function ProfileCard({ profile }: ProfileCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [showSuccessToast, setShowSuccessToast] = useState(false);

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
          <span>Profile updated successfully!</span>
        </div>
      )}

      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Professional Profile</CardTitle>
          <CardDescription>
            Core candidate identity, current role, and professional summary
          </CardDescription>
        </div>
        {!isEditing && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(true)}
            className="gap-1.5 text-xs"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit Profile</span>
          </Button>
        )}
      </CardHeader>

      <CardContent>
        {isEditing ? (
          <ProfileEditForm
            profile={profile}
            onSuccess={handleUpdateSuccess}
            onCancel={() => setIsEditing(false)}
          />
        ) : (
          <div className="space-y-6">
            {/* Header / Avatar block */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-terminal-warm text-terminal-primary flex items-center justify-center font-bold font-display text-xl border-2 border-terminal-warmBorder shrink-0 shadow-subtle">
                {profile.full_name ? profile.full_name.charAt(0).toUpperCase() : "C"}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold font-display text-terminal-dark">{profile.full_name}</h2>
                  <Badge variant="brand" withDot>Active</Badge>
                </div>
                <p className="text-sm font-medium text-terminal-primary font-sans">
                  {profile.headline || profile.current_role || "Candidate Profile"}
                </p>
              </div>
            </div>

            {/* Summary */}
            {profile.professional_summary ? (
              <div className="bg-terminal-warm/60 border border-terminal-warmBorder/80 rounded-card p-4">
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-1.5">
                  Professional Summary
                </h4>
                <p className="text-sm text-terminal-dark leading-relaxed whitespace-pre-line font-sans">
                  {profile.professional_summary}
                </p>
              </div>
            ) : (
              <p className="text-xs italic text-terminal-muted font-mono">
                No professional summary provided. Click "Edit Profile" to add one.
              </p>
            )}

            {/* Key Metadata Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
              <div className="flex items-center gap-2.5 p-3 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder">
                <Briefcase className="w-4 h-4 text-terminal-muted shrink-0" />
                <div className="min-w-0">
                  <span className="block text-[10px] uppercase font-mono font-bold text-terminal-muted">Current Role</span>
                  <span className="text-xs font-semibold text-terminal-dark truncate block font-sans">
                    {profile.current_role || "Not specified"}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2.5 p-3 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder">
                <Calendar className="w-4 h-4 text-terminal-muted shrink-0" />
                <div className="min-w-0">
                  <span className="block text-[10px] uppercase font-mono font-bold text-terminal-muted">Total Experience</span>
                  <span className="text-xs font-semibold text-terminal-dark truncate block font-mono">
                    {formatExperience(profile.total_experience_months)}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2.5 p-3 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder">
                <MapPin className="w-4 h-4 text-terminal-muted shrink-0" />
                <div className="min-w-0">
                  <span className="block text-[10px] uppercase font-mono font-bold text-terminal-muted">Location</span>
                  <span className="text-xs font-semibold text-terminal-dark truncate block font-sans">
                    {[profile.city, profile.country].filter(Boolean).join(", ") || "Remote / Not set"}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2.5 p-3 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder">
                <ShieldCheck className="w-4 h-4 text-terminal-muted shrink-0" />
                <div className="min-w-0">
                  <span className="block text-[10px] uppercase font-mono font-bold text-terminal-muted">Work Authorization</span>
                  <span className="text-xs font-semibold text-terminal-dark truncate block font-sans">
                    {profile.work_authorization || "Not specified"}
                  </span>
                </div>
              </div>
            </div>

            {/* Audit Dates */}
            <div className="flex items-center justify-between text-[11px] font-mono text-terminal-muted pt-3 border-t border-terminal-warmBorder">
              <span className="flex items-center gap-1">
                <User className="w-3 h-3 text-terminal-muted" />
                Profile ID: <code className="text-terminal-dark font-mono">{profile.id}</code>
              </span>
              <span className="flex items-center gap-1">
                <Globe className="w-3 h-3 text-terminal-muted" />
                Updated {formatDate(profile.updated_at)}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

