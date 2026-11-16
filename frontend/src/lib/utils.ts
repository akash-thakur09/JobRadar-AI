import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ProblemDetails } from "@/types/api";

/**
 * Merge Tailwind classes cleanly
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format ISO date string into readable local format
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return "—";
  }
}

/**
 * Format experience months into human readable string
 */
export function formatExperience(months: number): string {
  if (months <= 0) return "0 months";
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;

  if (years > 0 && remainingMonths > 0) {
    return `${years} yr${years > 1 ? "s" : ""} ${remainingMonths} mo${remainingMonths > 1 ? "s" : ""}`;
  }
  if (years > 0) {
    return `${years} year${years > 1 ? "s" : ""}`;
  }
  return `${remainingMonths} month${remainingMonths > 1 ? "s" : ""}`;
}

/**
 * Extract human-readable error message from backend RFC 7807 ProblemDetails or AxiosError
 */
export function extractErrorMessage(error: unknown, fallbackMessage = "An unexpected error occurred"): string {
  if (!error) return fallbackMessage;

  // Check if error response has ProblemDetails
  if (typeof error === "object" && error !== null) {
    const errObj = error as { response?: { data?: ProblemDetails | { detail?: string } }; message?: string };
    const problem = errObj.response?.data;

    if (problem) {
      if ("detail" in problem && problem.detail) {
        return problem.detail;
      }
      if ("title" in problem && problem.title) {
        return problem.title;
      }
    }

    if (errObj.message) {
      if (errObj.message.includes("Network Error")) {
        return "Unable to reach the JobRadar AI backend. Please verify that the API server is running.";
      }
      if (errObj.message.includes("timeout")) {
        return "Request timed out while communicating with the backend.";
      }
      return errObj.message;
    }
  }

  return fallbackMessage;
}

