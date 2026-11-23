import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { X, Plus } from "lucide-react";
import {
  preferencesUpdateSchema,
  type PreferencesUpdateFormValues,
} from "../schemas/preferencesSchema";
import type { CandidatePreferences, EmploymentType, WorkplaceType } from "@/types/candidate";
import { useUpdateCandidatePreferences } from "@/hooks/useCandidateProfile";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { extractErrorMessage } from "@/lib/utils";

export interface PreferencesEditFormProps {
  preferences: CandidatePreferences;
  onSuccess: () => void;
  onCancel: () => void;
}

const AVAILABLE_WORKPLACE_TYPES: Array<{ id: WorkplaceType; label: string }> = [
  { id: "REMOTE", label: "Remote" },
  { id: "HYBRID", label: "Hybrid" },
  { id: "ONSITE", label: "Onsite" },
];

const AVAILABLE_EMPLOYMENT_TYPES: Array<{ id: EmploymentType; label: string }> = [
  { id: "FULL_TIME", label: "Full Time" },
  { id: "PART_TIME", label: "Part Time" },
  { id: "CONTRACT", label: "Contract" },
  { id: "INTERNSHIP", label: "Internship" },
];

export function PreferencesEditForm({
  preferences,
  onSuccess,
  onCancel,
}: PreferencesEditFormProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const [titleInput, setTitleInput] = useState("");
  const [locationInput, setLocationInput] = useState("");

  const updateMutation = useUpdateCandidatePreferences();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<PreferencesUpdateFormValues>({
    resolver: zodResolver(preferencesUpdateSchema),
    defaultValues: {
      minimum_relevance_score: Number(preferences.minimum_relevance_score) || 70,
      max_job_age_days: preferences.max_job_age_days || 30,
      preferred_titles: preferences.preferred_titles || [],
      preferred_locations: preferences.preferred_locations || [],
      preferred_workplace_types: preferences.preferred_workplace_types || [],
      preferred_employment_types: preferences.preferred_employment_types || [],
    },
  });

  const preferredTitles = watch("preferred_titles");
  const preferredLocations = watch("preferred_locations");
  const preferredWorkplaceTypes = watch("preferred_workplace_types");
  const preferredEmploymentTypes = watch("preferred_employment_types");
  const minScore = watch("minimum_relevance_score");

  const handleAddTitle = () => {
    const trimmed = titleInput.trim();
    if (trimmed && !preferredTitles.includes(trimmed)) {
      setValue("preferred_titles", [...preferredTitles, trimmed], { shouldDirty: true });
      setTitleInput("");
    }
  };

  const handleRemoveTitle = (title: string) => {
    setValue(
      "preferred_titles",
      preferredTitles.filter((t) => t !== title),
      { shouldDirty: true }
    );
  };

  const handleAddLocation = () => {
    const trimmed = locationInput.trim();
    if (trimmed && !preferredLocations.includes(trimmed)) {
      setValue("preferred_locations", [...preferredLocations, trimmed], { shouldDirty: true });
      setLocationInput("");
    }
  };

  const handleRemoveLocation = (loc: string) => {
    setValue(
      "preferred_locations",
      preferredLocations.filter((l) => l !== loc),
      { shouldDirty: true }
    );
  };

  const toggleWorkplaceType = (wt: WorkplaceType) => {
    const exists = preferredWorkplaceTypes.includes(wt);
    const updated = exists
      ? preferredWorkplaceTypes.filter((t) => t !== wt)
      : [...preferredWorkplaceTypes, wt];
    setValue("preferred_workplace_types", updated, { shouldDirty: true });
  };

  const toggleEmploymentType = (et: EmploymentType) => {
    const exists = preferredEmploymentTypes.includes(et);
    const updated = exists
      ? preferredEmploymentTypes.filter((t) => t !== et)
      : [...preferredEmploymentTypes, et];
    setValue("preferred_employment_types", updated, { shouldDirty: true });
  };

  const onSubmit = async (values: PreferencesUpdateFormValues) => {
    setFormError(null);
    try {
      await updateMutation.mutateAsync({
        minimum_relevance_score: values.minimum_relevance_score,
        max_job_age_days: values.max_job_age_days,
        preferred_titles: values.preferred_titles,
        preferred_locations: values.preferred_locations,
        preferred_workplace_types: values.preferred_workplace_types,
        preferred_employment_types: values.preferred_employment_types,
      });
      onSuccess();
    } catch (err) {
      setFormError(extractErrorMessage(err, "Failed to update preferences. Please verify your entries."));
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {formError && (
        <Alert variant="error" title="Update Failed">
          {formError}
        </Alert>
      )}

      {/* Thresholds Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder">
        <div>
          <label className="block text-xs font-semibold font-display text-terminal-dark mb-1">
            Minimum Match Score Threshold ({minScore}%)
          </label>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            {...register("minimum_relevance_score")}
            className="w-full accent-terminal-primary cursor-pointer h-2 bg-terminal-warmSurface rounded-lg appearance-none border border-terminal-warmBorder"
          />
          <div className="flex justify-between text-[10px] font-mono text-terminal-muted mt-1">
            <span>0% (All Jobs)</span>
            <span className="font-semibold text-terminal-primary font-mono">{minScore}%</span>
            <span>100% (Strict)</span>
          </div>
          {errors.minimum_relevance_score && (
            <p className="text-xs text-terminal-errorText mt-1 font-mono">{errors.minimum_relevance_score.message}</p>
          )}
        </div>

        <Input
          label="Maximum Job Age (Days)"
          type="number"
          min={1}
          max={365}
          placeholder="30"
          helperText="Filter out postings older than this threshold"
          error={errors.max_job_age_days?.message}
          {...register("max_job_age_days")}
        />
      </div>

      {/* Target Job Titles */}
      <div>
        <label className="block text-xs font-semibold font-display text-terminal-dark mb-1.5">
          Target Job Titles
        </label>
        <div className="flex items-center gap-2 mb-2">
          <Input
            placeholder="e.g. Senior Backend Engineer"
            value={titleInput}
            onChange={(e) => setTitleInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAddTitle();
              }
            }}
            className="flex-1"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddTitle}
            className="gap-1 shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Title</span>
          </Button>
        </div>

        {preferredTitles.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {preferredTitles.map((title) => (
              <span
                key={title}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-card bg-[#FF5A36]/10 text-[#C93B1D] border border-[#FF5A36]/30 text-xs font-medium"
              >
                <span>{title}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveTitle(title)}
                  className="hover:text-terminal-dark ml-0.5"
                  aria-label={`Remove title ${title}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-terminal-muted italic font-mono">No target titles restricted yet. All titles allowed.</p>
        )}
      </div>

      {/* Target Locations */}
      <div>
        <label className="block text-xs font-semibold font-display text-terminal-dark mb-1.5">
          Target Locations
        </label>
        <div className="flex items-center gap-2 mb-2">
          <Input
            placeholder="e.g. San Francisco, CA or Remote"
            value={locationInput}
            onChange={(e) => setLocationInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAddLocation();
              }
            }}
            className="flex-1"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddLocation}
            className="gap-1 shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Location</span>
          </Button>
        </div>

        {preferredLocations.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {preferredLocations.map((loc) => (
              <span
                key={loc}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-card bg-terminal-warm border border-terminal-warmBorder text-terminal-dark text-xs font-medium"
              >
                <span>{loc}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveLocation(loc)}
                  className="hover:text-terminal-primary ml-0.5"
                  aria-label={`Remove location ${loc}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-terminal-muted italic font-mono">No specific locations restricted.</p>
        )}
      </div>

      {/* Workplace & Employment Types Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Workplace Types */}
        <div>
          <label className="block text-xs font-semibold font-display text-terminal-dark mb-1.5">
            Accepted Workplace Types
          </label>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_WORKPLACE_TYPES.map(({ id, label }) => {
              const isSelected = preferredWorkplaceTypes.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => toggleWorkplaceType(id)}
                  className={`px-3 py-1.5 rounded-card border text-xs font-medium font-mono transition-colors ${
                    isSelected
                      ? "bg-terminal-dark text-white border-terminal-dark shadow-subtle"
                      : "bg-terminal-warmSurface text-terminal-muted border-terminal-warmBorder hover:bg-terminal-warm"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Employment Types */}
        <div>
          <label className="block text-xs font-semibold font-display text-terminal-dark mb-1.5">
            Accepted Employment Types
          </label>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_EMPLOYMENT_TYPES.map(({ id, label }) => {
              const isSelected = preferredEmploymentTypes.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => toggleEmploymentType(id)}
                  className={`px-3 py-1.5 rounded-card border text-xs font-medium font-mono transition-colors ${
                    isSelected
                      ? "bg-terminal-dark text-white border-terminal-dark shadow-subtle"
                      : "bg-terminal-warmSurface text-terminal-muted border-terminal-warmBorder hover:bg-terminal-warm"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-end gap-3 pt-3 border-t border-terminal-warmBorder">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
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
          Save Preferences
        </Button>
      </div>
    </form>
  );
}

