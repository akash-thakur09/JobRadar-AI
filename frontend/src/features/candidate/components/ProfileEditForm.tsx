import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { profileUpdateSchema, type ProfileUpdateFormValues } from "../schemas/profileSchema";
import type { CandidateProfile } from "@/types/candidate";
import { useUpdateCandidateProfile } from "@/hooks/useCandidateProfile";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { extractErrorMessage } from "@/lib/utils";

export interface ProfileEditFormProps {
  profile: CandidateProfile;
  onSuccess: () => void;
  onCancel: () => void;
}

export function ProfileEditForm({ profile, onSuccess, onCancel }: ProfileEditFormProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const updateMutation = useUpdateCandidateProfile();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProfileUpdateFormValues>({
    resolver: zodResolver(profileUpdateSchema),
    defaultValues: {
      full_name: profile.full_name || "",
      headline: profile.headline || "",
      professional_summary: profile.professional_summary || "",
      current_role: profile.current_role || "",
      total_experience_months: profile.total_experience_months || 0,
      city: profile.city || "",
      country: profile.country || "",
      work_authorization: profile.work_authorization || "",
    },
  });

  const onSubmit = async (values: ProfileUpdateFormValues) => {
    setFormError(null);
    try {
      await updateMutation.mutateAsync({
        full_name: values.full_name,
        headline: values.headline,
        professional_summary: values.professional_summary,
        current_role: values.current_role,
        total_experience_months: values.total_experience_months,
        city: values.city,
        country: values.country,
        work_authorization: values.work_authorization,
      });
      onSuccess();
    } catch (err) {
      setFormError(extractErrorMessage(err, "Failed to update profile. Please verify your details."));
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {formError && (
        <Alert variant="error" title="Update Failed">
          {formError}
        </Alert>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Full Name"
          required
          placeholder="Jane Doe"
          error={errors.full_name?.message}
          {...register("full_name")}
        />

        <Input
          label="Current Role"
          placeholder="Senior Backend Engineer"
          error={errors.current_role?.message}
          {...register("current_role")}
        />
      </div>

      <Input
        label="Headline"
        placeholder="Staff Cloud Architect | Distributed Systems & Microservices"
        error={errors.headline?.message}
        helperText="Brief professional positioning statement"
        {...register("headline")}
      />

      <Textarea
        label="Professional Summary"
        rows={4}
        placeholder="Over 8 years of production experience architecting high-throughput backend services..."
        error={errors.professional_summary?.message}
        {...register("professional_summary")}
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Input
          label="Total Experience (Months)"
          type="number"
          min="0"
          placeholder="96"
          error={errors.total_experience_months?.message}
          helperText="e.g. 96 = 8 years"
          {...register("total_experience_months")}
        />

        <Input
          label="City"
          placeholder="Seattle"
          error={errors.city?.message}
          {...register("city")}
        />

        <Input
          label="Country"
          placeholder="United States"
          error={errors.country?.message}
          {...register("country")}
        />
      </div>

      <Input
        label="Work Authorization"
        placeholder="US Citizen / Permanent Resident / Authorized"
        error={errors.work_authorization?.message}
        {...register("work_authorization")}
      />

      <div className="flex items-center justify-end gap-3 pt-3 border-t border-terminal-warmBorder">
        <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
          Save Changes
        </Button>
      </div>
    </form>
  );
}

