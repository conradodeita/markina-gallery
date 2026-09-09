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
  minor_representation_reference?: string | null;
  consent_version?: string;
  legal_notice_version?: string;
  reference_retention_seconds?: number;
  candidate_retention_seconds?: number;
  max_reference_bytes?: number;
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
  poll_after_ms: number | null;
  estimate: {
    remaining_items: number;
    seconds: number | null;
    confidence: "unavailable" | "low" | "medium" | "high";
  };
  candidates?: FacialCandidate[];
};

export class FacialApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly retryAfterSeconds: number | null,
  ) {
    super(message);
    this.name = "FacialApiError";
  }
}

export type FacialIndexStatus = {
  state: "processing" | "completed" | "failed";
  rollout: {
    status: "prepared" | "active" | "suspended" | "revoked" | "unavailable";
    stage: "dark" | "canary" | "limited" | "general" | null;
    available: boolean;
  };
  progress: { ready: number; total: number };
  queued: number;
  processing: number;
  failed: number;
  coverage: { photos_with_faces: number; total: number; percent: number; detected_faces: number };
  waiting_previews: number;
  unindexed: number;
  failures: Array<{ job_id: string; photo_id: string; attempts: number; error_category: string }>;
  pagination: { page: number; page_size: number; total: number };
};

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const retryAfter = Number(response.headers.get("Retry-After"));
    throw new FacialApiError(
      payload?.detail ?? (response.status === 413
        ? "A foto excede o limite de 30 MB."
        : "Não foi possível concluir a operação facial."),
      response.status,
      Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    );
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
    representationReference?: string,
  ) => jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches`, {
    method: "POST",
    headers: {
      "content-type": "image/jpeg",
      "x-facial-consent-version": consentVersion,
      "x-facial-subject-declaration": subjectDeclaration,
      ...(representationReference ? { "x-facial-representation-reference": representationReference } : {}),
    },
    body: file,
  }),
  read: (galleryId: string, requestId: string) =>
    jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}`),
  latest: (galleryId: string) =>
    jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches/latest`),
  cancel: (galleryId: string, requestId: string) =>
    jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}`, { method: "DELETE" }),
  reject: (galleryId: string, requestId: string, photoId: string) =>
    jsonRequest<{ rejected: true }>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}/candidates/${photoId}`, { method: "DELETE" }),
  select: (galleryId: string, requestId: string, photoId: string) =>
    jsonRequest<Record<string, unknown>>(`/api/public-galleries/${galleryId}/facial-searches/${requestId}/candidates/${photoId}/selection`, { method: "POST" }),
};

export const facialAdminApi = {
  index: (galleryId: string) =>
    jsonRequest<FacialIndexStatus>(`/api/admin/parent-galleries/${galleryId}/facial-index`),
  retry: (galleryId: string, jobIds: string[]) =>
    jsonRequest<{ retried: number }>(`/api/admin/parent-galleries/${galleryId}/facial-index/retry`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_ids: jobIds }),
    }),
  reprocess: (galleryId: string) =>
    jsonRequest<{ photos_scanned: number; retried: number }>(`/api/admin/parent-galleries/${galleryId}/facial-index/reprocess`, {
      method: "POST",
    }),
};
