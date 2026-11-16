import { useState } from "react";
import { Award, Star, Plus, X, CheckCircle2 } from "lucide-react";
import type { CandidateSkill } from "@/types/candidate";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatExperience } from "@/lib/utils";
import { AddSkillModal } from "./AddSkillModal";
import { DeleteSkillModal } from "./DeleteSkillModal";

export interface SkillsListProps {
  skills: CandidateSkill[];
}

export function SkillsList({ skills }: SkillsListProps) {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [skillToDelete, setSkillToDelete] = useState<CandidateSkill | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const coreSkills = skills.filter((s) => s.is_core);
  const secondarySkills = skills.filter((s) => !s.is_core);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  return (
    <Card className="relative overflow-hidden">
      {toastMessage && (
        <div className="absolute top-3 right-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-card bg-terminal-success text-[#185C36] text-xs font-medium border border-terminal-success/40 shadow-dropdown transition-all animate-bounce">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Award className="w-4 h-4 text-terminal-primary" />
              <span>Evidence Vault Skills</span>
            </CardTitle>
            <CardDescription>
              Verified skills used for truthful Layer 1 & 2 matching and resume tailoring
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant="brand">{skills.length} Verified</Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAddModalOpen(true)}
              className="gap-1 text-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Skill</span>
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {skills.length === 0 ? (
          <div className="text-center py-8 rounded-card border-2 border-dashed border-terminal-warmBorder bg-terminal-warm/30 p-6">
            <Award className="w-8 h-8 text-terminal-muted mx-auto mb-2" />
            <h4 className="text-sm font-semibold font-display text-terminal-dark">No verified skills recorded</h4>
            <p className="text-xs text-terminal-muted max-w-sm mx-auto mt-1 mb-4 font-sans">
              Add verified competencies to enable accurate job matching and prevent resume tailoring hallucinations.
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsAddModalOpen(true)}
              className="gap-1.5 shadow-subtle"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add First Verified Skill</span>
            </Button>
          </div>
        ) : (
          <>
            {/* Core Skills */}
            {coreSkills.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2.5 flex items-center gap-1.5">
                  <Star className="w-3.5 h-3.5 text-terminal-amber fill-terminal-amber" />
                  <span>Core Competencies ({coreSkills.length})</span>
                </h4>
                <div className="flex flex-wrap gap-2">
                  {coreSkills.map((skill) => (
                    <div
                      key={skill.id}
                      className="group inline-flex items-center gap-2 px-3 py-1.5 rounded-card border border-[#B8E61A]/50 bg-[#D6FF3F]/20 text-[#3B4D00] text-xs font-semibold shadow-subtle transition-all hover:border-[#7EAB00]"
                    >
                      <span>{skill.skill_name}</span>
                      {skill.experience_months > 0 && (
                        <span className="text-[10px] font-mono text-[#3B4D00] font-bold px-1.5 py-0.5 rounded bg-[#D6FF3F]/40">
                          {formatExperience(skill.experience_months)}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => setSkillToDelete(skill)}
                        className="opacity-60 hover:opacity-100 hover:text-terminal-error transition-opacity ml-0.5 p-0.5"
                        title={`Remove ${skill.skill_name}`}
                        aria-label={`Remove skill ${skill.skill_name}`}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Secondary Skills */}
            {secondarySkills.length > 0 && (
              <div>
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted mb-2.5 flex items-center justify-between">
                  <span>Technical & Secondary Skills ({secondarySkills.length})</span>
                </h4>
                <div className="flex flex-wrap gap-2">
                  {secondarySkills.map((skill) => (
                    <div
                      key={skill.id}
                      className="group inline-flex items-center gap-2 px-2.5 py-1 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface text-terminal-dark text-xs transition-all hover:border-terminal-muted"
                    >
                      <span className="font-medium">{skill.skill_name}</span>
                      {skill.experience_months > 0 && (
                        <span className="text-[10px] font-mono text-terminal-muted">
                          ({formatExperience(skill.experience_months)})
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => setSkillToDelete(skill)}
                        className="opacity-40 hover:opacity-100 hover:text-terminal-error transition-opacity ml-0.5 p-0.5"
                        title={`Remove ${skill.skill_name}`}
                        aria-label={`Remove skill ${skill.skill_name}`}
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>

      {/* Add Skill Modal */}
      {isAddModalOpen && (
        <AddSkillModal
          existingSkills={skills}
          onClose={() => setIsAddModalOpen(false)}
          onSuccess={() => {
            setIsAddModalOpen(false);
            showToast("Skill successfully added to Evidence Vault!");
          }}
        />
      )}

      {/* Delete Skill Modal */}
      {skillToDelete && (
        <DeleteSkillModal
          skill={skillToDelete}
          onClose={() => setSkillToDelete(null)}
          onSuccess={() => {
            const name = skillToDelete.skill_name;
            setSkillToDelete(null);
            showToast(`Skill "${name}" removed from Evidence Vault.`);
          }}
        />
      )}
    </Card>
  );
}
