import { z } from "zod";

export const skillCreateSchema = z.object({
  skill_name: z
    .string()
    .min(1, "Skill name is required.")
    .max(100, "Skill name must not exceed 100 characters.")
    .refine((val) => val.trim().length > 0, "Skill name cannot be blank."),
  category: z
    .string()
    .max(50, "Category must not exceed 50 characters.")
    .default("general")
    .transform((val) => (val && val.trim() ? val.trim().toLowerCase() : "general")),
  experience_months: z
    .coerce
    .number({ invalid_type_error: "Must be a valid number of months" })
    .int("Must be a whole integer")
    .min(0, "Experience cannot be negative.")
    .default(0),
  is_core: z.boolean().default(false),
});

export type SkillCreateFormValues = z.infer<typeof skillCreateSchema>;

