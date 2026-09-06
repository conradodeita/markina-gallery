export type FacialSearchStatus =
  | "queued"
  | "waiting_index"
  | "validating_reference"
  | "searching"
  | "ranking"
  | "ready"
  | "no_face"
  | "multiple_faces"
  | "low_quality"
  | "index_incomplete"
  | "no_candidates"
  | "cancelled"
  | "expired"
  | "failed";

export type FacialSearchAvailability = {
  state: "unavailable" | "consent_required";
  manual_selection_available: true;
  minor_search_available: boolean;
  consent_version?: string;
  legal_notice_version?: string;
  reference_retention_seconds?: number;
  candidate_retention_seconds?: number;
  index?: { state: string; ready: number; total: number };
};

export type FacialCandidate = {
  photo_id: string;
  rank: number;
  quality_band: "best" | "other";
};

export type FacialSearchResult = {
  id: string;
  gallery_id: string;
  status: FacialSearchStatus;
  progress: {
    index: { ready: number; total: number };
    comparison: { done: number; total: number };
  };
  reference_deleted: boolean;
  expires_at: string;
  candidates?: FacialCandidate[];
};

export type FacialPolicy = {
  status: "disabled" | "pending" | "active" | "suspended";
  ready_for_activation: boolean;
  missing_requirements: string[];
  legal_notice_version: string | null;
  legal_basis_reference: string | null;
  retention_policy_version: string | null;
  minor_policy_version: string | null;
  model_version: string | null;
  quality_version: string | null;
  calibration_version: string | null;
  similarity_threshold_milli: number;
  index_generation: number;
  activated_at: string | null;
  suspended_at: string | null;
};

export type FacialIndexStatus = {
  state: "empty" | "pending" | "processing" | "ready" | "partial" | "failed";
  progress: { ready: number; total: number };
  queued: number;
  processing: number;
  failed: number;
  unindexed: number;
  failures: Array<{ job_id: string; photo_id: string; category: string }>;
  pagination: { page: number; page_size: number; total: number };
};

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail ?? "Não foi possível concluir a operação facial.");
  }
  return payload as T;
}

export const facialSearchApi = {
  availability: (galleryId: string) =>
    jsonRequest<FacialSearchAvailability>(`/api/public-galleries/${galleryId}/facial-search`),
  create: (
    galleryId: string,
    file: File,
    consentVersion: string,
    subjectDeclaration: "adult" | "minor",
  ) => jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches`, {
    method: "POST",
    headers: {
      "content-type": "image/jpeg",
      "x-facial-consent-version": consentVersion,
      "x-facial-subject-declaration": subjectDeclaration,
    },
    body: file,
  }),
  read: (galleryId: string, requestId: string) =>
    jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}`),
  cancel: (galleryId: string, requestId: string) =>
    jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}`, { method: "DELETE" }),
  reject: (galleryId: string, requestId: string, photoId: string) =>
    jsonRequest<{ rejected: true }>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}/candidates/${photoId}`, { method: "DELETE" }),
  select: (galleryId: string, requestId: string, photoId: string) =>
    jsonRequest<Record<string, unknown>>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}/candidates/${photoId}/selection`, { method: "POST" }),
};

export const facialAdminApi = {
  policy: (galleryId: string) =>
    jsonRequest<FacialPolicy>(`/api/admin/parent-galleries/${galleryId}/facial-policy`),
  index: (galleryId: string) =>
    jsonRequest<FacialIndexStatus>(`/api/admin/parent-galleries/${galleryId}/facial-index`),
  prepare: (galleryId: string, policy: FacialPolicy) =>
    jsonRequest<FacialPolicy>(`/api/admin/parent-galleries/${galleryId}/facial-policy`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        legal_notice_version: policy.legal_notice_version,
        legal_basis_reference: policy.legal_basis_reference,
        retention_policy_version: policy.retention_policy_version,
        minor_policy_version: policy.minor_policy_version,
        model_version: policy.model_version,
        quality_version: policy.quality_version,
        calibration_version: policy.calibration_version,
        similarity_threshold_milli: policy.similarity_threshold_milli,
      }),
    }),
  action: (galleryId: string, action: "activate" | "suspend" | "revoke") =>
    jsonRequest<FacialPolicy>(`/api/admin/parent-galleries/${galleryId}/facial-policy/${action}`, { method: "POST" }),
  retry: (galleryId: string, jobIds: string[]) =>
    jsonRequest<{ retried: number }>(`/api/admin/parent-galleries/${galleryId}/facial-index/retry`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_ids: jobIds }),
    }),
};
