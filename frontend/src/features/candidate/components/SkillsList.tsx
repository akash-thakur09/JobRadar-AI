import { Award, Star } from "lucide-react";
import type { CandidateSkill } from "@/types/candidate";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatExperience } from "@/lib/utils";

export interface SkillsListProps {
  skills: CandidateSkill[];
}

export function SkillsList({ skills }: SkillsListProps) {
  const coreSkills = skills.filter((s) => s.is_core);
  const secondarySkills = skills.filter((s) => !s.is_core);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Award className="w-4 h-4 text-terminal-primary" />
              <span>Verified Skills</span>
            </CardTitle>
            <CardDescription>
              Skills verified in Evidence Vault used for Layer 1 & 2 matching and resume tailoring
            </CardDescription>
          </div>
          <Badge variant="brand">{skills.length} Skills</Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {skills.length === 0 ? (
          <p className="text-xs italic text-terminal-muted font-mono">No verified skills recorded yet.</p>
        ) : (
          <>
            {/* Core Skills */}
            {coreSkills.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2 flex items-center gap-1.5">
                  <Star className="w-3.5 h-3.5 text-terminal-amber fill-terminal-amber" />
                  Core Competencies
                </h4>
                <div className="flex flex-wrap gap-2">
                  {coreSkills.map((skill) => (
                    <div
                      key={skill.id}
                      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-card border border-[#B8E61A]/50 bg-[#D6FF3F]/20 text-[#3B4D00] text-xs font-semibold shadow-subtle"
                    >
                      <span>{skill.skill_name}</span>
                      {skill.experience_months > 0 && (
                        <span className="text-[10px] font-mono text-[#3B4D00] font-bold px-1.5 py-0.5 rounded bg-[#D6FF3F]/40">
                          {formatExperience(skill.experience_months)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Secondary Skills */}
            {secondarySkills.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2">
                  Technical & Secondary Skills
                </h4>
                <div className="flex flex-wrap gap-2">
                  {secondarySkills.map((skill) => (
                    <div
                      key={skill.id}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface text-terminal-dark text-xs"
                    >
                      <span>{skill.skill_name}</span>
                      {skill.experience_months > 0 && (
                        <span className="text-[10px] font-mono text-terminal-muted">
                          ({formatExperience(skill.experience_months)})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

