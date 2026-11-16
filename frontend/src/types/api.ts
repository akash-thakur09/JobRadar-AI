/**
 * RFC 7807 Problem Details and Common API Response Types
 */

export interface InvalidParam {
  name: string;
  reason: string;
  type: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  correlation_id?: string;
  invalid_params?: InvalidParam[];
}

export interface PaginationMetadata {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMetadata;
}

