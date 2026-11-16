import { z } from "zod";
import type { EmploymentType, WorkplaceType } from "@/types/candidate";

const workplaceTypes: [WorkplaceType, ...WorkplaceType[]] = ["REMOTE", "HYBRID", "ONSITE"];
const employmentTypes: [EmploymentType, ...EmploymentType[]] = [
  "FULL_TIME",
  "PART_TIME",
  "CONTRACT",
  "INTERNSHIP",
];

export const preferencesUpdateSchema = z.object({
  minimum_relevance_score: z
    .coerce
    .number({ invalid_type_error: "Score must be a number between 0 and 100" })
    .min(0, "Minimum score cannot be less than 0%")
    .max(100, "Minimum score cannot exceed 100%")
    .default(70),
  max_job_age_days: z
    .coerce
    .number({ invalid_type_error: "Must be a valid number of days" })
    .int("Must be a whole integer")
    .min(1, "Max age must be at least 1 day")
    .max(365, "Max age cannot exceed 365 days")
    .default(30),
  preferred_titles: z.array(z.string().trim().min(1)).default([]),
  preferred_locations: z.array(z.string().trim().min(1)).default([]),
  preferred_workplace_types: z.array(z.enum(workplaceTypes)).default([]),
  preferred_employment_types: z.array(z.enum(employmentTypes)).default([]),
});

export type PreferencesUpdateFormValues = z.infer<typeof preferencesUpdateSchema>;

