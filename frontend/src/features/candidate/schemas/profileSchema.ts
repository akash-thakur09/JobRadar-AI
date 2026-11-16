import { z } from "zod";

export const profileUpdateSchema = z.object({
  full_name: z
    .string()
    .min(1, "Full name is required.")
    .max(150, "Full name must not exceed 150 characters.")
    .refine((val) => val.trim().length > 0, "Full name cannot be blank or whitespace only."),
  headline: z
    .string()
    .max(255, "Headline must not exceed 255 characters.")
    .optional()
    .nullable()
    .transform((val) => (val && val.trim() ? val.trim() : null)),
  professional_summary: z
    .string()
    .optional()
    .nullable()
    .transform((val) => (val && val.trim() ? val.trim() : null)),
  current_role: z
    .string()
    .max(150, "Current role must not exceed 150 characters.")
    .optional()
    .nullable()
    .transform((val) => (val && val.trim() ? val.trim() : null)),
  total_experience_months: z
    .coerce
    .number({ invalid_type_error: "Must be a valid number of months" })
    .int("Must be a whole integer")
    .min(0, "Experience cannot be negative.")
    .default(0),
  city: z
    .string()
    .max(100, "City must not exceed 100 characters.")
    .optional()
    .nullable()
    .transform((val) => (val && val.trim() ? val.trim() : null)),
  country: z
    .string()
    .max(100, "Country must not exceed 100 characters.")
    .optional()
    .nullable()
    .transform((val) => (val && val.trim() ? val.trim() : null)),
  work_authorization: z
    .string()
    .max(50, "Work authorization must not exceed 50 characters.")
    .optional()
    .nullable()
    .transform((val) => (val && val.trim() ? val.trim() : null)),
});

export type ProfileUpdateFormValues = z.infer<typeof profileUpdateSchema>;

