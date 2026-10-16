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
  storage_context?: string;
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
  match_class?: "matched" | "ambiguous";
};

export type FaceRegion = { id: string; x: number; y: number; width: number; height: number };

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

export function facialProgressPercent(done: number, total: number): number | undefined {
  if (!Number.isFinite(done) || !Number.isFinite(total) || total <= 0) return undefined;
  const boundedDone = Math.max(0, Math.min(total, done));
  return Math.floor((boundedDone / total) * 100);
}

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

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", cache: "no-store", ...init });
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
  regions: (galleryId: string, photoId: string) =>
    jsonRequest<{ regions: FaceRegion[]; auto_threshold: number }>(`/api/public-galleries/${galleryId}/photos/${photoId}/face-regions`),
  createFromRegion: (galleryId: string, regionId: string) =>
    jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/face-region-searches`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ face_region_id: regionId }),
    }),
  availability: (galleryId: string) =>
    jsonRequest<FacialSearchAvailability>(`/api/public-galleries/${galleryId}/facial-search`),
  create: (
    galleryId: string,
    file: File,
    consentVersion: string,
    subjectDeclaration: "conditional",
    representationReference?: string,
  ) => jsonRequest<FacialSearchResult>(`/api/public-galleries/${galleryId}/facial-searches`, {
    method: "POST",
    headers: {
      "content-type": "image/jpeg",
      "x-facial-consent-version": consentVersion,
      "x-facial-consent-accepted": "true",
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
