import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { X, Award, Info } from "lucide-react";
import { skillCreateSchema, type SkillCreateFormValues } from "../schemas/skillSchema";
import type { CandidateSkill } from "@/types/candidate";
import { useAddCandidateSkill } from "@/hooks/useCandidateProfile";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { extractErrorMessage } from "@/lib/utils";

export interface AddSkillModalProps {
  existingSkills: CandidateSkill[];
  onClose: () => void;
  onSuccess: () => void;
}

const COMMON_CATEGORIES = [
  { value: "backend", label: "Backend Engineering" },
  { value: "frontend", label: "Frontend & UI" },
  { value: "database", label: "Databases & Storage" },
  { value: "cloud", label: "Cloud & Infrastructure" },
  { value: "devops", label: "DevOps & CI/CD" },
  { value: "ai_ml", label: "AI & Machine Learning" },
  { value: "general", label: "General & Foundational" },
];

export function AddSkillModal({
  existingSkills,
  onClose,
  onSuccess,
}: AddSkillModalProps) {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const addMutation = useAddCandidateSkill();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SkillCreateFormValues>({
    resolver: zodResolver(skillCreateSchema),
    defaultValues: {
      skill_name: "",
      category: "backend",
      experience_months: 12,
      is_core: false,
    },
  });

  const onSubmit = async (values: SkillCreateFormValues) => {
    setErrorMsg(null);

    // Frontend duplicate check
    const normalizedInput = values.skill_name.trim().toLowerCase();
    const alreadyExists = existingSkills.some(
      (s) => s.skill_name.toLowerCase() === normalizedInput
    );

    if (alreadyExists) {
      setErrorMsg(`Skill "${values.skill_name.trim()}" is already registered in your Evidence Vault.`);
      return;
    }

    try {
      await addMutation.mutateAsync({
        skill_name: values.skill_name.trim(),
        category: values.category,
        experience_months: values.experience_months,
        is_core: values.is_core,
      });
      onSuccess();
    } catch (err) {
      setErrorMsg(extractErrorMessage(err, "Failed to register skill. Please check your inputs."));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-terminal-dark/70 backdrop-blur-xs">
      <div className="bg-terminal-warmSurface rounded-card shadow-dropdown border border-terminal-warmBorder max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-terminal-warmBorder">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-card bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-primary shadow-subtle">
              <Award className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold font-display text-terminal-dark">Add Verified Skill</h3>
              <p className="text-xs text-terminal-muted">Register verified candidate competency</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm transition-colors"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="p-5 space-y-4">
            {errorMsg && (
              <Alert variant="error" title="Cannot Register Skill">
                {errorMsg}
              </Alert>
            )}

            <div className="p-3 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder text-xs text-terminal-dark space-y-1">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-terminal-primary shrink-0 mt-0.5" />
                <p className="text-[11px] text-terminal-muted font-sans leading-relaxed">
                  Skills in your Evidence Vault are strictly used for matching. Common technology aliases (e.g. <code className="text-terminal-dark font-mono font-medium">postgres</code> &rarr; <code className="text-terminal-dark font-mono font-medium">postgresql</code>) are automatically normalized.
                </p>
              </div>
            </div>

            <Input
              label="Skill Name"
              required
              placeholder="e.g. PostgreSQL, React, Python, Docker"
              error={errors.skill_name?.message}
              {...register("skill_name")}
            />

            <div>
              <label className="block text-xs font-semibold font-display text-terminal-dark mb-1.5">
                Technical Category
              </label>
              <select
                {...register("category")}
                className="w-full px-3 py-2 text-xs rounded-card border border-terminal-warmBorder bg-terminal-warmSurface text-terminal-dark font-sans focus:outline-none focus:ring-2 focus:ring-terminal-primary"
              >
                {COMMON_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
              {errors.category && (
                <p className="text-xs text-terminal-errorText mt-1 font-mono">{errors.category.message}</p>
              )}
            </div>

            <Input
              label="Experience (Months)"
              type="number"
              min={0}
              placeholder="24"
              helperText="e.g. 24 = 2 years of production experience"
              error={errors.experience_months?.message}
              {...register("experience_months")}
            />

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="is_core"
                {...register("is_core")}
                className="w-4 h-4 rounded-sharp border-terminal-warmBorder text-terminal-primary focus:ring-terminal-primary accent-terminal-primary cursor-pointer"
              />
              <label htmlFor="is_core" className="text-xs font-medium text-terminal-dark cursor-pointer select-none">
                Designate as <span className="font-semibold text-terminal-dark">Core Competency</span> (high weight in Layer 2 scoring)
              </label>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-terminal-warmBorder bg-terminal-warm rounded-b-card flex items-center justify-end gap-2.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              className="shadow-subtle"
            >
              Register Skill
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

