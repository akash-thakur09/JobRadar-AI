import { describe, it, expect, vi, beforeEach } from "vitest";
import type { AxiosResponse } from "axios";
import { apiClient, apiGet, apiPost, apiPut, apiDelete, ApiError } from "../api-client";
import type { ProblemDetails } from "@/types/api";

describe("api-client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("handles successful GET request", async () => {
    const mockData = { id: "123", full_name: "Test Candidate" };
    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: mockData,
      status: 200,
      statusText: "OK",
      headers: {},
      config: {} as AxiosResponse["config"],
    });

    const result = await apiGet<typeof mockData>("/candidate/profile");
    expect(result).toEqual(mockData);
    expect(apiClient.get).toHaveBeenCalledWith("/candidate/profile", undefined);
  });

  it("handles successful POST request", async () => {
    const mockPayload = { candidate_profile_id: "c-123" };
    const mockResponse = { id: "run-456", status: "PENDING" };
    vi.spyOn(apiClient, "post").mockResolvedValueOnce({
      data: mockResponse,
      status: 202,
      statusText: "Accepted",
      headers: {},
      config: {} as AxiosResponse["config"],
    });

    const result = await apiPost<typeof mockResponse, typeof mockPayload>("/pipeline-runs", mockPayload);
    expect(result).toEqual(mockResponse);
    expect(apiClient.post).toHaveBeenCalledWith("/pipeline-runs", mockPayload, undefined);
  });

  it("handles successful PUT request", async () => {
    const mockPayload = { full_name: "Updated Name" };
    const mockResponse = { id: "c-123", full_name: "Updated Name" };
    vi.spyOn(apiClient, "put").mockResolvedValueOnce({
      data: mockResponse,
      status: 200,
      statusText: "OK",
      headers: {},
      config: {} as AxiosResponse["config"],
    });

    const result = await apiPut<typeof mockResponse, typeof mockPayload>("/candidate/profile", mockPayload);
    expect(result).toEqual(mockResponse);
  });

  it("handles successful DELETE request", async () => {
    vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
      data: undefined,
      status: 204,
      statusText: "No Content",
      headers: {},
      config: {} as AxiosResponse["config"],
    });

    const result = await apiDelete<void>("/candidate/skills/s-1");
    expect(result).toBeUndefined();
  });

  it("formats ApiError from RFC 7807 problem details response", () => {
    const problem: ProblemDetails = {
      type: "https://api.jobradar.ai/v1/errors/validation-error",
      title: "Validation Error",
      status: 422,
      detail: "Full name cannot be blank.",
      invalid_params: [{ name: "full_name", reason: "Blank", type: "value_error" }],
    };

    const err = new ApiError(problem.detail, problem.status, problem);
    expect(err.name).toBe("ApiError");
    expect(err.status).toBe(422);
    expect(err.message).toBe("Full name cannot be blank.");
    expect(err.problem?.invalid_params).toHaveLength(1);
    expect(err.isNetworkError).toBe(false);
  });

  it("identifies network error", () => {
    const err = new ApiError("Network error: unable to connect", 0, undefined, true, false);
    expect(err.isNetworkError).toBe(true);
    expect(err.isTimeout).toBe(false);
    expect(err.status).toBe(0);
  });

  it("identifies timeout error", () => {
    const err = new ApiError("Backend request timed out", 0, undefined, false, true);
    expect(err.isTimeout).toBe(true);
    expect(err.isNetworkError).toBe(false);
  });
});

