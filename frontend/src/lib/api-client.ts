import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig } from "axios";
import type { ProblemDetails } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const TIMEOUT_MS = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS) || 15000;

export class ApiError extends Error {
  public status: number;
  public problem?: ProblemDetails;
  public isNetworkError: boolean;
  public isTimeout: boolean;

  constructor(
    message: string,
    status: number,
    problem?: ProblemDetails,
    isNetworkError = false,
    isTimeout = false
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
    this.isNetworkError = isNetworkError;
    this.isTimeout = isTimeout;
  }
}

/**
 * Creates and configures the centralized Axios instance
 */
function createApiClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: BASE_URL,
    timeout: TIMEOUT_MS,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, application/problem+json",
    },
  });

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ProblemDetails>) => {
      // 1. Network / Reachability Error
      if (!error.response) {
        const isTimeout = error.code === "ECONNABORTED" || error.message.toLowerCase().includes("timeout");
        const msg = isTimeout
          ? `Backend request timed out after ${TIMEOUT_MS / 1000} seconds.`
          : "Network error: unable to connect to the JobRadar AI backend service.";

        return Promise.reject(new ApiError(msg, 0, undefined, !isTimeout, isTimeout));
      }

      // 2. HTTP Error with RFC 7807 Problem Details
      const status = error.response.status;
      const data = error.response.data;

      let message = `API request failed with status ${status}`;
      if (data && typeof data === "object") {
        if ("detail" in data && typeof data.detail === "string") {
          message = data.detail;
        } else if ("title" in data && typeof data.title === "string") {
          message = data.title;
        }
      }

      return Promise.reject(new ApiError(message, status, data));
    }
  );

  return instance;
}

export const apiClient = createApiClient();

/**
 * Centralized API helper methods with strict typing
 */
export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.get<T>(url, config);
  return response.data;
}

export async function apiPost<T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.post<T>(url, body, config);
  return response.data;
}

export async function apiPut<T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.put<T>(url, body, config);
  return response.data;
}

export async function apiDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.delete<T>(url, config);
  return response.data;
}

