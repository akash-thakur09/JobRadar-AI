import { Sliders, Award, Briefcase, UserCheck, MapPin, Sparkles, Check, X } from "lucide-react";
import type { JobMatchDetail } from "@/types/matches";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";

export interface DeterministicScoreBreakdownProps {
  match: JobMatchDetail;
}

export function DeterministicScoreBreakdown({ match }: DeterministicScoreBreakdownProps) {
  const detScore = Number(match.deterministic_score) || 0;
  const skillScore = Number(match.skill_score) || 0;
  const expScore = Number(match.experience_score) || 0;
  const titleScore = Number(match.title_score) || 0;
  const prefScore = Number(match.preference_score) || 0;

  const details = match.match_explanation_details?.deterministic_breakdown;
  const skillsData = details?.skills;
  const matchedSkills = skillsData?.matched_skills || [];
  const missingSkills = skillsData?.missing_skills || [];
  const bonusData = details?.bonus;

  return (
    <Card className="border-terminal-warmBorder">
      <CardHeader className="pb-3 border-b border-terminal-warmBorder/60">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <Sliders className="w-4 h-4 text-terminal-primary" />
            <span>Layer 2: Deterministic Weighted Score Breakdown</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-terminal-muted">Score:</span>
            <span className="text-base font-mono font-bold text-terminal-dark px-2 py-0.5 rounded-card bg-terminal-warm border border-terminal-warmBorder">
              {detScore.toFixed(2)} / 100.00
            </span>
          </div>
        </div>
        <CardDescription className="text-xs">
          Transparent mathematical evaluation of candidate qualifications without generative AI variability
        </CardDescription>
      </CardHeader>

      <CardContent className="p-6 space-y-6">
        {/* Dimension 1: Skills Match (40 pts) */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-terminal-primary" />
              <span className="font-semibold text-terminal-dark">1. Skills Alignment</span>
              <span className="text-terminal-muted">(Max 40 pts)</span>
            </div>
            <span className="font-mono font-bold text-terminal-dark">{skillScore.toFixed(1)} / 40.0 pts</span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 rounded-full bg-terminal-warm overflow-hidden border border-terminal-warmBorder">
            <div
              className="h-full bg-terminal-primary transition-all duration-300"
              style={{ width: `${Math.min(100, (skillScore / 40) * 100)}%` }}
            />
          </div>

          {/* Skills pills */}
          <div className="space-y-2 pt-1">
            {matchedSkills.length > 0 && (
              <div>
                <span className="text-[11px] font-mono text-[#185C36] font-semibold block mb-1.5">
                  Matched Skills ({matchedSkills.length}):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {matchedSkills.map((sk) => (
                    <span
                      key={sk}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono bg-[#5BCB8A]/15 text-[#185C36] border border-[#5BCB8A]/30"
                    >
                      <Check className="w-3 h-3 text-[#185C36]" />
                      <span>{sk}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {missingSkills.length > 0 && (
              <div>
                <span className="text-[11px] font-mono text-terminal-muted font-semibold block mb-1.5">
                  Unmatched Target Technologies ({missingSkills.length}):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {missingSkills.map((sk) => (
                    <span
                      key={sk}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono bg-terminal-warm text-terminal-muted border border-terminal-warmBorder"
                    >
                      <X className="w-3 h-3 text-terminal-muted" />
                      <span>{sk}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Dimension 2: Experience Relevance (20 pts) */}
        <div className="space-y-2 border-t border-terminal-warmBorder/60 pt-4">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-terminal-muted" />
              <span className="font-semibold text-terminal-dark">2. Experience & Seniority Tier</span>
              <span className="text-terminal-muted">(Max 20 pts)</span>
            </div>
            <span className="font-mono font-bold text-terminal-dark">{expScore.toFixed(1)} / 20.0 pts</span>
          </div>

          <div className="w-full h-2 rounded-full bg-terminal-warm overflow-hidden border border-terminal-warmBorder">
            <div
              className="h-full bg-terminal-dark transition-all duration-300"
              style={{ width: `${Math.min(100, (expScore / 20) * 100)}%` }}
            />
          </div>

          {details?.experience && (
            <p className="text-xs font-mono text-terminal-muted">
              Candidate Tier: <span className="font-semibold text-terminal-dark capitalize">{String(details.experience.candidate_seniority || "verified")}</span> &bull; 
              Required Tier: <span className="font-semibold text-terminal-dark capitalize">{String(details.experience.job_seniority || "specified")}</span>
            </p>
          )}
        </div>

        {/* Dimension 3: Title Relevance (15 pts) */}
        <div className="space-y-2 border-t border-terminal-warmBorder/60 pt-4">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-terminal-muted" />
              <span className="font-semibold text-terminal-dark">3. Role Title Similarity</span>
              <span className="text-terminal-muted">(Max 15 pts)</span>
            </div>
            <span className="font-mono font-bold text-terminal-dark">{titleScore.toFixed(1)} / 15.0 pts</span>
          </div>

          <div className="w-full h-2 rounded-full bg-terminal-warm overflow-hidden border border-terminal-warmBorder">
            <div
              className="h-full bg-terminal-muted transition-all duration-300"
              style={{ width: `${Math.min(100, (titleScore / 15) * 100)}%` }}
            />
          </div>
        </div>

        {/* Dimension 4: Workplace & Location (15 pts) */}
        <div className="space-y-2 border-t border-terminal-warmBorder/60 pt-4">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-terminal-muted" />
              <span className="font-semibold text-terminal-dark">4. Workplace & Location Preference</span>
              <span className="text-terminal-muted">(Max 15 pts)</span>
            </div>
            <span className="font-mono font-bold text-terminal-dark">{prefScore.toFixed(1)} / 15.0 pts</span>
          </div>

          <div className="w-full h-2 rounded-full bg-terminal-warm overflow-hidden border border-terminal-warmBorder">
            <div
              className="h-full bg-terminal-muted transition-all duration-300"
              style={{ width: `${Math.min(100, (prefScore / 15) * 100)}%` }}
            />
          </div>
        </div>

        {/* Dimension 5: Freshness Bonus (10 pts) */}
        {bonusData && (
          <div className="space-y-2 border-t border-terminal-warmBorder/60 pt-4">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-terminal-amber" />
                <span className="font-semibold text-terminal-dark">5. Posting Freshness Bonus</span>
                <span className="text-terminal-muted">(Max 10 pts)</span>
              </div>
              <span className="font-mono font-bold text-terminal-dark">
                {Number(bonusData.score || 0).toFixed(1)} / 10.0 pts
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
