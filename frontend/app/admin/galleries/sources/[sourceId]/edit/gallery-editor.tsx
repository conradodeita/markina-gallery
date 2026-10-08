"use client";
import { jpegStorageKey, uploadJpeg } from "../../../../../upload-jpeg";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ChangeEvent, type FormEvent, type MouseEvent, useEffect, useMemo, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../../../../ui-kit";
import {
  ClientCreateForm,
  type ClientDirectoryItem,
  ClientEditorDialog,
} from "../../../../clients/client-controls";
import { ClientGalleryCard, type ClientGalleryRow } from "../../../client-gallery-card";
import { FacialPolicyPanel } from "../../../facial-policy-panel";
import PreviewAdjustmentPanel from "../../../preview-adjustment-panel";
import { FolderProcessingPanel } from "../../../folder-processing-panel";
import { GlobalPixSummary, type GlobalPix } from "../../../../settings/pix-panel";
import { formatBrazilianCurrency, maskBrazilianCurrencyInput, parseBrazilianCurrency, type PriceTier } from "../../../pricing-rules";

type StepId = "ajustes" | "vendas" | "detalhes" | "imagens" | "clientes";
type EditorStep = { id: StepId; label: string; status: "complete" | "pending" | "unavailable"; available: boolean };
type CoverReadiness = { status: "missing" | "processing" | "failed" | "ready"; message: string };
type Editor = { cover_readiness?: CoverReadiness; gallery: { id: string; name: string; event_name: string; description: string; active: boolean; access_mode: "standard" | "invite_only" | "collective_protected"; unlisted_link: string | null; public_link?: { status: string; capability_id: string | null; expires_at: string | null; secret_available: boolean }; cover_photo_id: string | null; cover_preview_url: string | null; folder_display_mode: string; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string }; steps: EditorStep[]; counts: { folders: number; registrations: number; derived_galleries: number }; capabilities: Record<string, boolean>; actions: { can_create_folder: boolean; can_upload: boolean; can_complete?: boolean } };
type PublicationCounts = { published: number; ready_to_publish: number; processing: number; failed: number };
type Folder = { id: string; name: string; status: string; position: number; photo_count: number; preview_url: string | null; released_at: string | null; publication_counts?: PublicationCounts };
type Photo = { id: string; name: string; preview_url: string | null; status: string; publication_state?: "published" | "ready_to_publish" | "processing" | "failed"; available?: boolean; width?: number | null; height?: number | null; error: string | null; can_delete: boolean; is_cover: boolean };
type ClientRow = ClientGalleryRow;
type ClientOption = ClientDirectoryItem;
type PricingMode = "fixed" | "progressive" | "legacy_volume";
type PricingPreset = { id: string; code: string; name: string; label: string; version: number; active: boolean; tiers: PriceTier[] };
type PricingQuote = { quantity: number; parcels: Array<PriceTier & { quantity: number; subtotal_cents: number }>; base_total_cents: number; savings_cents: number; total_cents: number };
type SalesData = { payment_required?: boolean; available: boolean; reason?: string; capabilities: string[]; pricing_mode: PricingMode; fixed_unit_price_cents: number | null; progressive_pricing_preset_id: string | null; pricing_snapshot: Record<string, unknown> | null; pricing_review_required: boolean; tiers: PriceTier[]; pix: GlobalPix; sales_message: string; selection_duration_days: number | null; favorites_enabled: boolean; comments_enabled: boolean };
type GalleryLink = { status: "active" | "unavailable" | "legacy_unrecoverable"; capability_id: string | null; expires_at: string | null; secret_available: boolean; link: string | null };
type FontOption = { token: string; label: string; category: "sans" | "editorial" | "handwritten"; css_family: string };
type CoverOption = { id: string; name: string; source: "content" | "cover_assets"; status: "ready" | "processing" | "failed"; preview_url: string | null; width: number | null; height: number | null; error?: string | null };
type DetailsData = { cover_readiness?: CoverReadiness; available: boolean; capabilities: string[]; font_options: FontOption[]; cover_options: CoverOption[]; settings: { cover_photo_id: string | null; cover_preview_url: string | null; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string } };
type VisualPreview = { folder_display_mode: string; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string };
type UnlinkPreview = { operation_type: "unlink_client"; target: { parent_gallery_id: string; parent_gallery_name: string; client_id: string; client_name: string }; inventory: { remove: Record<string, number>; preserve: Record<string, number | Record<string, number>> }; consequences: { gallery_relationship_removed: boolean; private_gallery_removed: boolean; client_preserved: boolean; commercial_history_preserved: boolean; other_gallery_relationships_preserved: boolean; restoration_available_after_start: boolean } };
type LifecycleOperation = { operation_id: string; status: string; status_url: string; last_error: string | null; progress: { label: string; percent: number; failed_step: string | null }; actions: { can_cancel: boolean; can_retry: boolean; should_poll: boolean; poll_after_ms: number | null } };
type PhotoBulkDeleteResult = { deleted_ids?: string[]; blocked_ids?: string[]; missing_ids?: string[] };

const PHOTO_BULK_DELETE_BATCH_SIZE = 100;

export function photoBulkDeleteBatches(photoIds: string[]) {
  const uniquePhotoIds = [...new Set(photoIds)];
  return Array.from(
    { length: Math.ceil(uniquePhotoIds.length / PHOTO_BULK_DELETE_BATCH_SIZE) },
    (_, index) => uniquePhotoIds.slice(
      index * PHOTO_BULK_DELETE_BATCH_SIZE,
      (index + 1) * PHOTO_BULK_DELETE_BATCH_SIZE,
    ),
  );
}

function bulkDeleteMessage(result: Required<PhotoBulkDeleteResult>) {
  const parts = [`${result.deleted_ids.length} foto(s) excluída(s)`];
  if (result.blocked_ids.length) parts.push(`${result.blocked_ids.length} protegida(s) por regra comercial`);
  if (result.missing_ids.length) parts.push(`${result.missing_ids.length} já ausente(s)`);
  return `${parts.join("; ")}.`;
}

const stepOrder: StepId[] = ["ajustes", "vendas", "detalhes", "imagens", "clientes"];
function folderPublicationClass(folder: Folder) {
  if (folder.publication_counts?.failed) return "has-failures";
  if (folder.publication_counts?.processing) return "is-processing";
  if (folder.publication_counts?.ready_to_publish) return "is-ready";
  if (folder.publication_counts?.published) return "is-published";
  return "is-empty";
}

function FolderPublicationSummary({ folder }: { folder: Folder }) {
  const counts = folder.publication_counts ?? { published: folder.status === "released" ? folder.photo_count : 0, ready_to_publish: 0, processing: 0, failed: 0 };
  return <span className="folder-publication-summary" aria-label={`Publicação de ${folder.name}`}>
    <small className="is-published">{counts.published} disponíveis</small>
    <small className="is-ready">{counts.ready_to_publish} aguardando liberação automática</small>
    <small className="is-processing">{counts.processing} preparando prévia</small>
    <small className="has-failures">{counts.failed} falhas</small>
  </span>;
}

async function jsonRequest(path: string, init?: RequestInit) {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? "Não foi possível concluir a operação.");
  }
  return response.status === 204 ? { cleanup_pending: response.headers.get("X-Asset-Cleanup") === "failed" } : response.json();
}

export default function GalleryEditor({ sourceId, step, initialFolderId = "" }: { sourceId: string; step: string; initialFolderId?: string }) {
  const router = useRouter();
  const currentStep = step as StepId;
  const [editor, setEditor] = useState<Editor | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [selectedPhotoIds, setSelectedPhotoIds] = useState<string[]>([]);
  const [expandedPhoto, setExpandedPhoto] = useState<Photo | null>(null);
  const [openFolderId, setOpenFolderId] = useState("");
  const [linkedClients, setLinkedClients] = useState<ClientRow[]>([]);
  const [clientOptions, setClientOptions] = useState<ClientOption[]>([]);
  const [clientQuery, setClientQuery] = useState("");
  const [clientEditTarget, setClientEditTarget] = useState<ClientOption | null>(null);
  const [sales, setSales] = useState<SalesData | null>(null);
  const [salesError, setSalesError] = useState("");
  const [pricingPresets, setPricingPresets] = useState<PricingPreset[]>([]);
  const [fixedPriceInput, setFixedPriceInput] = useState("R$ 0,00");
  const [quoteQuantity, setQuoteQuantity] = useState(60);
  const [pricingQuote, setPricingQuote] = useState<PricingQuote | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [confirmLegacyConversion, setConfirmLegacyConversion] = useState(false);
  const [publicLink, setPublicLink] = useState<GalleryLink | null>(null);
  const [accessBusy, setAccessBusy] = useState("");
  const [dirty, setDirty] = useState(false);
  const [savingStep, setSavingStep] = useState(false);
  const [details, setDetails] = useState<DetailsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [bulkDeleteBusy, setBulkDeleteBusy] = useState(false);
  const [folderDeleteBusy, setFolderDeleteBusy] = useState(false);
  const [uploadState, setUploadState] = useState<{ phase: "idle" | "uploading" | "success" | "error"; current: number; total: number; filename?: string }>({ phase: "idle", current: 0, total: 0 });
  const [failed, setFailed] = useState(false);
  const [visualPreview, setVisualPreview] = useState<VisualPreview | null>(null);
  const [unlinkPreview, setUnlinkPreview] = useState<UnlinkPreview | null>(null);
  const [unlinkOperation, setUnlinkOperation] = useState<LifecycleOperation | null>(null);
  const [unlinkBusy, setUnlinkBusy] = useState(false);
  const [unlinkTarget, setUnlinkTarget] = useState<{ clientId: string; name: string } | null>(null);
  const [unlinkError, setUnlinkError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [facialRefresh, setFacialRefresh] = useState(0);
  const [detailsPollingError, setDetailsPollingError] = useState("");
  const [detailsPollingRetry, setDetailsPollingRetry] = useState(0);
  const previewDialog = useRef<HTMLDivElement>(null);
  const uploadInput = useRef<HTMLInputElement>(null);
  const coverUploadInput = useRef<HTMLInputElement>(null);
  const uploadForm = useRef<HTMLFormElement>(null);
  const unlinkIdempotencyKey = useRef("");
  const loadedStep = useRef<StepId | null>(null);

  useEffect(() => {
    if (currentStep !== "clientes") return;
    let active = true;
    const refreshClients = () => {
      void jsonRequest(`/api/admin/parent-galleries/${sourceId}/clients`)
        .then((result) => { if (active) setLinkedClients(result.clients ?? []); })
        .catch(() => { if (active) setMessage("Não foi possível atualizar os pagamentos. Tente novamente."); });
    };
    window.addEventListener("focus", refreshClients);
    return () => { active = false; window.removeEventListener("focus", refreshClients); };
  }, [currentStep, sourceId]);

  useEffect(() => {
    if (expandedPhoto) previewDialog.current?.focus();
  }, [expandedPhoto]);

  useEffect(() => {
    if (!dirty) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [dirty]);

  useEffect(() => {
    if (currentStep !== "detalhes" || !details?.cover_options?.some((option) => option.status === "processing")) return;
    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const nextDetails = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/details`) as DetailsData;
        if (!active) return;
        setDetails(nextDetails);
        setDetailsPollingError("");
      } catch (error) {
        if (!active) return;
        setDetailsPollingError(error instanceof Error ? error.message : "Não foi possível atualizar o estado da capa.");
      }
    }, 1500);
    return () => { active = false; window.clearTimeout(timer); };
  }, [currentStep, details, detailsPollingRetry, sourceId]);

  useEffect(() => {
    if (currentStep !== "imagens" || !folders.some((folder) => folder.publication_counts?.processing)) return;
    const timer = window.setTimeout(() => setRefresh((value) => value + 1), 1500);
    return () => window.clearTimeout(timer);
  }, [currentStep, folders]);

  useEffect(() => {
    if (!unlinkOperation?.actions.should_poll) return;
    const timer = window.setTimeout(async () => {
      try {
        const nextOperation = await jsonRequest(`/api${unlinkOperation.status_url}`) as LifecycleOperation;
        setUnlinkOperation(nextOperation);
        if (nextOperation.status === "completed") setRefresh((value) => value + 1);
      } catch (error) {
        setUnlinkError(error instanceof Error ? error.message : "Não foi possível atualizar a desvinculação.");
      }
    }, unlinkOperation.actions.poll_after_ms ?? 1000);
    return () => window.clearTimeout(timer);
  }, [unlinkOperation]);

  useEffect(() => {
    let active = true;
    const isInitialStepLoad = loadedStep.current !== currentStep;
    queueMicrotask(() => {
      if (!active) return;
      if (isInitialStepLoad) setLoading(true);
      setFailed(false);
    });
    const editorRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/editor`);
    let sectionRequest: Promise<unknown> = Promise.resolve(null);
    if (currentStep === "ajustes") sectionRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/settings`);
    if (currentStep === "vendas") sectionRequest = Promise.all([
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/sales`),
      jsonRequest("/api/admin/pricing-presets"),
    ]);
    if (currentStep === "detalhes") sectionRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/details`);
    if (currentStep === "imagens") sectionRequest = jsonRequest(`/api/admin/parent-galleries/${sourceId}/folders`);
    if (currentStep === "clientes") sectionRequest = Promise.all([
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/clients`),
      jsonRequest(`/api/admin/clients${clientQuery ? `?query=${encodeURIComponent(clientQuery)}` : ""}`),
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/public-link`),
    ]);
    Promise.all([editorRequest, sectionRequest])
      .then(([editorData, sectionData]) => {
        if (!active) return;
        setEditor(editorData as Editor);
        const visual = (editorData as Editor).gallery;
        setVisualPreview((current) => current ?? { folder_display_mode: visual.folder_display_mode ?? "individual", cover_title_font: visual.cover_title_font ?? "system-sans", cover_title_color: visual.cover_title_color ?? "#FFFFFF", cover_title_size: visual.cover_title_size ?? 32, cover_title_position: visual.cover_title_position ?? "bottom-left" });
        if (currentStep === "vendas") {
          const [salesData, presetData] = sectionData as [SalesData, { presets: PricingPreset[] }];
          setSales(salesData);
          setSalesError("");
          setPricingPresets(presetData.presets ?? []);
          setFixedPriceInput(formatBrazilianCurrency(salesData.fixed_unit_price_cents ?? salesData.tiers?.[0]?.unit_price_cents ?? 0));
          setConfirmLegacyConversion(false);
          setPricingQuote(null);
        }
        if (currentStep === "detalhes") {
          setDetails(sectionData as DetailsData);
          setDetailsPollingError("");
        }
        if (currentStep === "imagens") {
          const folderData = sectionData as { folders: Folder[] };
          setFolders(folderData.folders ?? []);
          const requested = initialFolderId && folderData.folders?.some((folder) => folder.id === initialFolderId)
            ? initialFolderId
            : openFolderId && folderData.folders?.some((folder) => folder.id === openFolderId) ? openFolderId : "";
          if (requested) queueMicrotask(() => inspectFolder(requested));
        }
        if (currentStep === "clientes") {
          const [clientData, optionData, linkData] = sectionData as [{ clients: ClientRow[] }, { clients: ClientOption[] }, GalleryLink];
          setLinkedClients(clientData.clients ?? []);
          setClientOptions(optionData.clients ?? []);
          setPublicLink(linkData);
        }
        loadedStep.current = currentStep;
      })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [clientQuery, currentStep, initialFolderId, openFolderId, refresh, sourceId]);

  const currentIndex = stepOrder.indexOf(currentStep);
  const previous = currentIndex > 0 ? stepOrder[currentIndex - 1] : null;
  const next = currentIndex < stepOrder.length - 1 ? stepOrder[currentIndex + 1] : null;
  const selectedFolder = useMemo(
    () => folders.find((folder) => folder.id === openFolderId) ?? null,
    [folders, openFolderId],
  );
  const currentCover = details?.cover_options?.find((option) => option.id === details.settings?.cover_photo_id) ?? details?.cover_options?.[0] ?? null;
  const coverPreviewUrl = currentCover?.preview_url ?? details?.settings?.cover_preview_url ?? editor?.gallery.cover_preview_url ?? null;
  const coverReadiness = details?.cover_readiness ?? editor?.cover_readiness;
  const coverReady = coverReadiness?.status === "ready" && !detailsPollingError;
  const coverRequiredMessage = coverReadiness?.message ?? "Defina uma imagem de capa para salvar Detalhes e concluir a galeria.";
  const titleFontFamily = details?.font_options?.find((option) => option.token === visualPreview?.cover_title_font)?.css_family ?? "var(--font-system-sans)";
  const activeEditableForm = currentStep === "ajustes" ? "gallery-settings-step" : currentStep === "vendas" ? "gallery-sales-step" : currentStep === "detalhes" ? "gallery-details-step" : null;

  function confirmDiscard(event: MouseEvent<HTMLAnchorElement>) {
    if (!dirty) return;
    if (!window.confirm("Descartar as alterações ainda não salvas desta etapa?")) {
      event.preventDefault();
      return;
    }
    setDirty(false);
  }

  function advanceAfterSave() {
    setDirty(false);
    if (next) router.push(`/admin/galleries/sources/${sourceId}/edit/${next}`);
  }

  async function mutate(path: string, method: string, body?: object) {
    try {
      const data = await jsonRequest(path, {
        method,
        headers: body ? { "content-type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      setMessage("Alteração salva com sucesso.");
      setRefresh((value) => value + 1);
      return data;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível concluir a operação.");
      return null;
    }
  }

  async function inspectFolder(folderId: string) {
    setOpenFolderId(folderId);
    setPhotos([]);
    setSelectedPhotoIds([]);
    if (!folderId) return;
    try {
      const data = await jsonRequest(`/api/admin/photo-folders/${folderId}/photos`);
      setPhotos(data.photos ?? []);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível abrir a pasta.");
    }
  }

  async function deleteFolder(folder: Folder) {
    if (folderDeleteBusy || !window.confirm(`Excluir a pasta “${folder.name}” e suas ${folder.photo_count} foto(s)? As fotos serão removidas também das galerias que as utilizam. Nomes das fotos, seleções e todos os estados financeiros permanecem no histórico, sem imagens. Esta ação não pode ser desfeita.`)) return;
    setFolderDeleteBusy(true);
    try {
      const result = await jsonRequest(`/api/admin/photo-folders/${folder.id}`, { method: "DELETE" });
      if (openFolderId === folder.id) { setOpenFolderId(""); setPhotos([]); setSelectedPhotoIds([]); setExpandedPhoto(null); }
      setFolders((current) => current.filter((item) => item.id !== folder.id));
      setMessage(result?.cleanup_pending ? "Pasta removida. A limpeza dos arquivos continuará em segundo plano." : "Pasta e fotos excluídas.");
      setRefresh((value) => value + 1);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível excluir a pasta."); }
    finally { setFolderDeleteBusy(false); }
  }

  async function deletePhoto(photo: Photo) {
    if (!window.confirm(`Excluir ${photo.name}? Esta ação não pode ser desfeita.`)) return;
    try {
      const result = await jsonRequest(`/api/admin/photo-folders/${openFolderId}/photos/${photo.id}`, { method: "DELETE" });
      setMessage(result?.cleanup_pending ? "Foto removida. A limpeza do arquivo continuará em segundo plano." : "Foto excluída da pasta.");
      setExpandedPhoto(null);
      await inspectFolder(openFolderId);
      setRefresh((value) => value + 1);
      setFacialRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível excluir a foto.");
    }
  }

  async function deleteSelectedPhotos() {
    if (bulkDeleteBusy) return;
    const batches = photoBulkDeleteBatches(selectedPhotoIds);
    const uniquePhotoIds = batches.flat();
    const selectedSet = new Set(uniquePhotoIds);
    const eligible = photos.filter((photo) => selectedSet.has(photo.id) && photo.can_delete);
    if (!eligible.length) return;
    if (!window.confirm(`Excluir ${eligible.length} foto(s) selecionada(s)? Esta ação não pode ser desfeita.`)) return;
    const result: Required<PhotoBulkDeleteResult> = { deleted_ids: [], blocked_ids: [], missing_ids: [] };
    let completedBatches = 0;
    let finalMessage = "";
    setBulkDeleteBusy(true);
    try {
      for (const batch of batches) {
        const batchResult = await jsonRequest(`/api/admin/photo-folders/${openFolderId}/photos`, {
          method: "DELETE",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ photo_ids: batch }),
        }) as PhotoBulkDeleteResult;
        result.deleted_ids.push(...(Array.isArray(batchResult?.deleted_ids) ? batchResult.deleted_ids : []));
        result.blocked_ids.push(...(Array.isArray(batchResult?.blocked_ids) ? batchResult.blocked_ids : []));
        result.missing_ids.push(...(Array.isArray(batchResult?.missing_ids) ? batchResult.missing_ids : []));
        completedBatches += 1;
      }
      finalMessage = bulkDeleteMessage(result);
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Não foi possível excluir as fotos.";
      finalMessage = completedBatches
        ? `Resultado parcial: ${bulkDeleteMessage(result)} A exclusão não foi concluída: ${reason}`
        : reason;
    } finally {
      await inspectFolder(openFolderId);
      setRefresh((value) => value + 1);
      setFacialRefresh((value) => value + 1);
      setMessage(finalMessage);
      setBulkDeleteBusy(false);
    }
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savingStep) return;
    setSavingStep(true);
    const form = new FormData(event.currentTarget);
    const saved = await mutate(`/api/admin/parent-galleries/${sourceId}/settings`, "PATCH", {
      name: form.get("name"),
      event_name: form.get("event_name"),
      description: form.get("description"),
      active: form.get("active") === "on",
      ...(form.get("access_mode") ? { access_mode: form.get("access_mode") } : {}),
    });
    if (saved) advanceAfterSave();
    setSavingStep(false);
  }

  async function saveVisualSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savingStep) return;
    if (!coverReady) {
      setMessage(detailsPollingError || coverRequiredMessage);
      return;
    }
    setSavingStep(true);
    const form = new FormData(event.currentTarget);
    const saved = await mutate(`/api/admin/parent-galleries/${sourceId}/settings`, "PATCH", {
      cover_title_font: form.get("cover_title_font"), cover_title_color: form.get("cover_title_color"),
      cover_title_size: Number(form.get("cover_title_size")), cover_title_position: form.get("cover_title_position"),
    });
    if (saved) advanceAfterSave();
    setSavingStep(false);
  }

  function updateVisualPreview(event: FormEvent<HTMLFormElement>) {
    const form = new FormData(event.currentTarget);
    setVisualPreview({ folder_display_mode: visualPreview?.folder_display_mode ?? editor?.gallery.folder_display_mode ?? "individual", cover_title_font: String(form.get("cover_title_font") ?? "system-sans"), cover_title_color: String(form.get("cover_title_color") ?? "#FFFFFF"), cover_title_size: Number(form.get("cover_title_size") ?? 32), cover_title_position: String(form.get("cover_title_position") ?? "bottom-left") });
  }

  async function completeGallery() {
    if (savingStep) return;
    setSavingStep(true);
    try {
      const latest = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/editor`) as Editor;
      setEditor(latest);
      if (latest.actions.can_complete !== true || latest.cover_readiness?.status !== "ready") {
        setMessage(latest.cover_readiness?.message ?? coverRequiredMessage);
        return;
      }
      setDirty(false);
      router.push(`/admin/galleries/sources/${sourceId}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível verificar a capa. Tente novamente.");
    } finally {
      setSavingStep(false);
    }
  }

  async function saveSales(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sales || savingStep) return;
    setSalesError("");
    if (sales.payment_required !== false && sales.pricing_mode === "legacy_volume") {
      setSalesError("Escolha preço fixo ou uma tabela progressiva para converter a configuração legada.");
      return;
    }
    const fixedUnitPriceCents = sales.pricing_mode === "fixed"
      ? parseBrazilianCurrency(fixedPriceInput)
      : null;
    if (sales.payment_required !== false && sales.pricing_mode === "fixed" && (fixedUnitPriceCents === null || fixedUnitPriceCents <= 0)) {
      setSalesError("Informe o valor unitário como moeda brasileira, por exemplo R$ 7,00.");
      return;
    }
    if (sales.payment_required !== false && sales.pricing_mode === "progressive" && !sales.progressive_pricing_preset_id) {
      setSalesError("Escolha uma tabela de preço progressivo da sua conta.");
      return;
    }
    setSavingStep(true);
    try {
      const saved = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/sales`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          payment_required: sales.payment_required !== false,
          pricing_mode: sales.payment_required !== false ? sales.pricing_mode : null,
          fixed_unit_price_cents: sales.payment_required !== false ? fixedUnitPriceCents : null,
          progressive_pricing_preset_id: sales.payment_required !== false && sales.pricing_mode === "progressive" ? sales.progressive_pricing_preset_id : null,
          confirm_legacy_conversion: confirmLegacyConversion,
          sales_message: sales.sales_message,
          selection_duration_days: sales.selection_duration_days,
          favorites_enabled: sales.favorites_enabled,
          comments_enabled: sales.comments_enabled,
        }),
      }) as SalesData;
      setSales(saved);
      setFixedPriceInput(formatBrazilianCurrency(saved.fixed_unit_price_cents ?? saved.tiers?.[0]?.unit_price_cents ?? 0));
      setConfirmLegacyConversion(false);
      setMessage("Configuração de Vendas salva.");
      setRefresh((value) => value + 1);
      advanceAfterSave();
    } catch (error) {
      setSalesError(error instanceof Error ? error.message : "Não foi possível salvar a configuração de Vendas.");
    } finally {
      setSavingStep(false);
    }
  }

  async function simulatePricing() {
    if (!sales?.progressive_pricing_preset_id || quoteLoading) return;
    setQuoteLoading(true);
    setPricingQuote(null);
    try {
      const result = await jsonRequest(`/api/admin/pricing-presets/${sales.progressive_pricing_preset_id}/quote?quantity=${quoteQuantity}`) as PricingQuote;
      setPricingQuote(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível simular o valor.");
    } finally {
      setQuoteLoading(false);
    }
  }

  async function copyAccessLink(link: string | null, label: string) {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setMessage(`${label} copiado.`);
    } catch {
      setMessage("Não foi possível copiar automaticamente. Selecione o endereço exibido.");
    }
  }

  async function createPublicLink() {
    if (accessBusy) return;
    setAccessBusy("public-create");
    try {
      const result = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/public-link`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      }) as GalleryLink;
      setPublicLink(result);
      setMessage("Link permanente da Galeria pública criado.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atualizar o link público.");
    } finally {
      setAccessBusy("");
    }
  }

  async function saveFolderOrganization(event: ChangeEvent<HTMLSelectElement>) {
    const mode = event.target.value;
    const saved = await mutate(`/api/admin/parent-galleries/${sourceId}/settings`, "PATCH", { folder_display_mode: mode });
    if (saved) setVisualPreview((current) => current ? { ...current, folder_display_mode: mode } : current);
  }

  async function uploadCover(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadState({ phase: "uploading", current: 1, total: 1, filename: file.name });
    try {
      const registered = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/cover-photos`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ filename: file.name, display_name: file.name, idempotency_key: crypto.randomUUID() }),
      });
      await jsonRequest(`/api${registered.upload_url}`, { method: "PUT", headers: { "content-type": "image/jpeg" }, body: file });
      setUploadState({ phase: "success", current: 1, total: 1, filename: file.name });
      setMessage("Capa definida e enviada para processamento. A prévia será atualizada automaticamente.");
      setRefresh((value) => value + 1);
    } catch (error) {
      setUploadState({ phase: "error", current: 0, total: 1, filename: file.name });
      setMessage(error instanceof Error ? error.message : "Não foi possível enviar a capa.");
    } finally {
      event.target.value = "";
    }
  }

  async function saveImagesAndAdvance() {
    if (savingStep) return;
    setSavingStep(true);
    try {
      const processing = folders.reduce((total, folder) => total + (folder.publication_counts?.processing ?? 0), 0);
      const failed = folders.reduce((total, folder) => total + (folder.publication_counts?.failed ?? 0), 0);
      setMessage(processing || failed
        ? `Organização salva. ${processing} foto(s) ainda preparando prévia e ${failed} com falha; as concluídas aparecem automaticamente.`
        : "Organização salva. As fotos processadas já estão disponíveis automaticamente.");
      advanceAfterSave();
    } finally {
      setSavingStep(false);
    }
  }

  async function createFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const created = await mutate(`/api/admin/parent-galleries/${sourceId}/folders`, "POST", { name: form.get("name") });
    if (created) formElement.reset();
  }

  async function uploadPhotos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const folderId = String(form.get("folder") ?? "");
    const input = formElement.elements.namedItem("jpeg") as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!folderId || !files.length) return;
    setUploadState({ phase: "uploading", current: 0, total: files.length });
    for (const [index, file] of files.entries()) {
      setUploadState({ phase: "uploading", current: index + 1, total: files.length, filename: file.name });
      try {
        const storageKey = await jpegStorageKey(sourceId, folderId, file);
        const photo = await jsonRequest(`/api/admin/photo-folders/${folderId}/photos`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            storage_key: storageKey,
          }),
        });
        if (index === 0) setFacialRefresh((value) => value + 1);
        await uploadJpeg(`/api/admin/photo-assets/${photo.id}/source`, file, () => setMessage("Aguardando o processamento liberar espaço para continuar o envio."));
      } catch (error) {
        setUploadState({ phase: "error", current: index, total: files.length, filename: file.name });
        setMessage(error instanceof Error ? error.message : `Falha ao enviar ${file.name}.`);
        return;
      }
    }
    setUploadState({ phase: "success", current: files.length, total: files.length });
    setMessage(`${files.length} foto(s) enviada(s). As prévias serão preparadas e disponibilizadas automaticamente.`);
    setRefresh((value) => value + 1);
    await inspectFolder(folderId);
    formElement.reset();
  }

  async function bindClient(clientId: string, name: string) {
    const linked = await mutate(`/api/admin/parent-galleries/${sourceId}/clients/${clientId}`, "PUT", {});
    if (linked) setMessage(`${name} vinculada à galeria.`);
  }

  async function openUnlinkConfirmation(person: ClientRow) {
    setUnlinkBusy(true);
    setUnlinkTarget({ clientId: person.client_id, name: person.name });
    setUnlinkOperation(null);
    setUnlinkError("");
    try {
      const preview = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/clients/${person.client_id}/unlink-inventory`) as UnlinkPreview;
      unlinkIdempotencyKey.current = crypto.randomUUID();
      setUnlinkPreview(preview);
    } catch (error) {
      setUnlinkError(error instanceof Error ? error.message : "Não foi possível preparar a desvinculação.");
    } finally {
      setUnlinkBusy(false);
    }
  }

  async function confirmUnlink() {
    if (!unlinkPreview || unlinkBusy) return;
    setUnlinkBusy(true);
    setUnlinkError("");
    try {
      const operation = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/clients/${unlinkPreview.target.client_id}`, {
        method: "DELETE",
        headers: { "Idempotency-Key": unlinkIdempotencyKey.current },
      }) as LifecycleOperation;
      setUnlinkOperation(operation);
      setUnlinkPreview(null);
    } catch (error) {
      setUnlinkError(error instanceof Error ? error.message : "Não foi possível iniciar a desvinculação.");
    } finally {
      setUnlinkBusy(false);
    }
  }

  async function unlinkOperationAction(action: "cancel" | "retry") {
    if (!unlinkOperation || unlinkBusy) return;
    setUnlinkBusy(true);
    setUnlinkError("");
    try {
      const operation = await jsonRequest(`/api/admin/gallery-lifecycle-operations/${unlinkOperation.operation_id}/${action}`, { method: "POST" }) as LifecycleOperation;
      setUnlinkOperation(operation);
      if (operation.status === "cancelled") setRefresh((value) => value + 1);
    } catch (error) {
      setUnlinkError(error instanceof Error ? error.message : "Não foi possível atualizar a desvinculação.");
    } finally {
      setUnlinkBusy(false);
    }
  }

  if (failed) return <SystemState tone="error" title="Galeria indisponível" detail="Não foi possível carregar o editor. Atualize a página ou entre novamente." />;
  if (loading || !editor) return <SystemState tone="loading" title="Abrindo a galeria" detail="Consultando etapas, permissões e conteúdo." />;

  return (
    <main className="admin-shell gallery-editor-shell">
      <div className="gallery-editor-heading">
        <div>
          <Link href="/admin/galleries" onClick={confirmDiscard}>← Galerias</Link>
          <p className="eyebrow">Galeria do evento · link não listado</p>
          <h1>{editor.gallery.name}</h1>
          <p className="intro">Organize as pastas, revise as fotos e vincule clientes sem sair desta galeria.</p>
        </div>
        <StatusBadge tone={editor.gallery.active ? "success" : "danger"}>{editor.gallery.active ? "Ativa" : "Bloqueada"}</StatusBadge>
      </div>
      <nav className="gallery-stepper" aria-label="Etapas da galeria">
        {editor.steps.map((item, index) => (
          <Link key={item.id} href={`/admin/galleries/sources/${sourceId}/edit/${item.id}`} onClick={item.id === currentStep ? undefined : confirmDiscard} aria-current={item.id === currentStep ? "step" : undefined} className={item.id === currentStep ? "is-current" : ""}>
            <span>{index + 1}</span><strong>{item.label}</strong><small>{item.status === "complete" ? "Concluída" : item.status === "unavailable" ? "Em breve" : "Pendente"}</small>
          </Link>
        ))}
      </nav>

      {currentStep === "ajustes" ? (
        <form id="gallery-settings-step" className="gallery-editor-panel gallery-settings-form" onSubmit={saveSettings} onChange={() => setDirty(true)}>
          <div className="section-heading"><div><p className="eyebrow">Etapa 1</p><h2>Ajustes da galeria</h2></div></div>
          <label>Título da galeria<input name="name" defaultValue={editor.gallery.name} required /></label>
          <label>Evento<input name="event_name" defaultValue={editor.gallery.event_name} /></label>
          <label>Descrição administrativa<textarea name="description" defaultValue={editor.gallery.description} rows={4} /><small className="field-hint">Uso interno do fotógrafo para registrar contexto, observações e pendências desta galeria.</small></label>
          {editor.gallery.access_mode === "collective_protected" ? <p role="status">Modo protegido legado: o acesso continua bloqueado. Escolher outro modo altera a possibilidade de entrada e navegação, sem ativar vínculos pendentes.</p> : null}
          <label>Modo de acesso<select name="access_mode" defaultValue={editor.gallery.access_mode === "collective_protected" ? "" : editor.gallery.access_mode}>{editor.gallery.access_mode === "collective_protected" ? <option value="">Manter modo protegido legado</option> : null}<option value="standard">Padrão</option><option value="invite_only">Somente convite individual</option></select><small className="field-hint">A autorização é aplicada pelo backend; nenhuma opção libera prévias antes do login.</small></label>
          <div className="access-mode-hints" role="region" aria-label="Como funcionam os modos de acesso"><article><strong>Padrão</strong><p>Quem recebe o link válido e confirma o código no WhatsApp pode entrar, sem cadastro prévio pelo fotógrafo.</p></article><article><strong>Somente convite individual</strong><p>Só entram clientes vinculadas pelo fotógrafo ou autorizadas por convite individual. Encaminhar o link geral não dá acesso a outra pessoa.</p></article><p>Nos dois modos, cada cliente vê as pastas comuns e somente as exclusivas atribuídas a ela. Seleções e compras continuam individuais.</p></div>
          <label className="gallery-toggle"><input name="active" type="checkbox" defaultChecked={editor.gallery.active} /> Galeria ativa</label>
        </form>
      ) : null}

      {currentStep === "vendas" ? (
        <section className="gallery-editor-panel">
          <p className="eyebrow">Etapa {currentIndex + 1}</p>
          <h2>Vendas</h2>
          {!sales?.available ? <SystemState title="Configuração comercial indisponível" detail={sales?.reason ?? "O backend não habilitou esta capacidade."} /> : (
            <form id="gallery-sales-step" className="gallery-sales-editor" onSubmit={saveSales} onChange={() => { setDirty(true); setSalesError(""); }}>
              {salesError ? <p className="form-message form-message--error" role="alert">{salesError}</p> : null}
              <fieldset className="gallery-sales-section">
                <legend>Preço das fotos</legend>
                <p>Escolha um valor fixo para qualquer quantidade ou aplique uma tabela progressiva cadastrada na sua conta. Pedidos existentes não são recalculados.</p>
                {sales.pricing_review_required || sales.pricing_mode === "legacy_volume" ? <div className="notice" role="alert"><strong>Configuração legada precisa de revisão.</strong><span>As faixas antigas não serão convertidas automaticamente. Escolha um dos modos abaixo e confirme a conversão.</span></div> : null}
                <div className="gallery-pricing-mode" role="radiogroup" aria-label="Modo de preço">
                  <label><input type="radio" name="pricing_mode" value="fixed" checked={sales.pricing_mode === "fixed"} onChange={() => { setSales((current) => current ? { ...current, pricing_mode: "fixed", progressive_pricing_preset_id: null } : current); setPricingQuote(null); }} /> Preço fixo por foto</label>
                  <label><input type="radio" name="pricing_mode" value="progressive" checked={sales.pricing_mode === "progressive"} onChange={() => setSales((current) => current ? { ...current, pricing_mode: "progressive", fixed_unit_price_cents: null } : current)} /> Preço progressivo por faixas</label>
                </div>
                {sales.pricing_mode === "fixed" ? <label>Valor unitário da foto<input name="fixed_unit_price" inputMode="numeric" value={fixedPriceInput} onChange={(event) => setFixedPriceInput(maskBrazilianCurrencyInput(event.target.value))} placeholder="R$ 7,00" required={sales.payment_required !== false} /></label> : null}
                {sales.pricing_mode === "progressive" ? <div className="gallery-progressive-pricing">
                  <label>Tabela da sua conta<select name="progressive_pricing_preset_id" value={sales.progressive_pricing_preset_id ?? ""} onChange={(event) => { setSales((current) => current ? { ...current, progressive_pricing_preset_id: event.target.value || null } : current); setPricingQuote(null); }} required={sales.payment_required !== false}><option value="">Selecione código — nome</option>{pricingPresets.map((preset) => <option key={preset.id} value={preset.id}>{preset.label}</option>)}</select></label>
                  {!pricingPresets.length ? <p className="field-hint">Nenhuma tabela ativa. <Link href="/admin/pricing">Cadastre uma tabela da sua conta</Link> antes de salvar.</p> : null}
                  <div className="gallery-pricing-simulator">
                    <label>Quantidade para simular<input type="number" min={1} max={10000} value={quoteQuantity} onChange={(event) => setQuoteQuantity(Number(event.target.value))} /></label>
                    <MarkinaButton type="button" variant="secondary" disabled={!sales.progressive_pricing_preset_id || quoteLoading} onClick={simulatePricing}>{quoteLoading ? "Calculando…" : "Simular valor"}</MarkinaButton>
                  </div>
                  {pricingQuote ? <div className="gallery-pricing-quote" aria-live="polite"><strong>{pricingQuote.quantity} fotos · {formatBrazilianCurrency(pricingQuote.total_cents)}</strong><span>Economia de {formatBrazilianCurrency(pricingQuote.savings_cents)}</span><dl>{pricingQuote.parcels.map((parcel) => <div key={parcel.minimum_quantity}><dt>{parcel.quantity} foto(s) a {formatBrazilianCurrency(parcel.unit_price_cents)}</dt><dd>{formatBrazilianCurrency(parcel.subtotal_cents)}</dd></div>)}</dl></div> : null}
                </div> : null}
                {sales.pricing_review_required || sales.pricing_mode === "legacy_volume" ? <label className="gallery-toggle"><input type="checkbox" checked={confirmLegacyConversion} onChange={(event) => setConfirmLegacyConversion(event.target.checked)} /> Confirmo a substituição das faixas legadas para esta galeria</label> : null}
              </fieldset>
              <fieldset className="gallery-sales-section">
                <legend>PIX da sua conta</legend>
                <GlobalPixSummary pix={sales.pix} />
                <Link href="/admin/settings#pix">Configurar PIX em Configurações</Link>
              </fieldset>
              <fieldset className="gallery-sales-section">
                <legend>Jornada da cliente</legend>
                <label className="gallery-toggle"><input type="checkbox" checked={sales.payment_required !== false} onChange={(event) => setSales((current) => current ? { ...current, payment_required: event.target.checked } : current)} /> Pagamento obrigatório?</label>
                {sales.payment_required === false ? <p>O sistema será usado somente para seleção. A cliente finaliza sem cobrança, com preços e totais ocultos.</p> : null}
                <label>Mensagem comercial<textarea name="sales_message" rows={4} value={sales.sales_message} onChange={(event) => setSales((current) => current ? { ...current, sales_message: event.target.value } : current)} /></label>
                <label>Prazo padrão de seleção (dias)<input name="selection_duration_days" type="number" min={1} max={3650} value={sales.selection_duration_days ?? 14} onChange={(event) => setSales((current) => current ? { ...current, selection_duration_days: Number(event.target.value) } : current)} required /></label>
                <label className="gallery-toggle"><input name="favorites_enabled" type="checkbox" checked={sales.favorites_enabled} onChange={(event) => setSales((current) => current ? { ...current, favorites_enabled: event.target.checked } : current)} /> Permitir favoritos</label>
                <label className="gallery-toggle"><input name="comments_enabled" type="checkbox" checked={sales.comments_enabled} onChange={(event) => setSales((current) => current ? { ...current, comments_enabled: event.target.checked } : current)} /> Permitir comentários</label>
              </fieldset>
            </form>
          )}
        </section>
      ) : null}

      {currentStep === "detalhes" ? (
        <section className="gallery-editor-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Etapa 3</p>
              <h2>Detalhes e apresentação</h2>
              <p className="gallery-scope-note">Configure como esta galeria será apresentada. A marca-d’água vale para as galerias da sua conta e fica em Configurações.</p>
            </div>
          </div>
          <form id="gallery-details-step" className="gallery-settings-form gallery-visual-settings" onSubmit={saveVisualSettings} onChange={(event) => { setDirty(true); updateVisualPreview(event); }}>
            <div className="gallery-customization-layout">
              <div className="gallery-customization-panels">
                <fieldset className="gallery-customization-panel">
                  <legend>Capa e título</legend>
                  <p>A capa é obrigatória para salvar esta etapa e concluir a galeria.</p>
                  {!coverReady ? <p className="gallery-scope-note" role="status">{coverRequiredMessage}</p> : null}
                  <input ref={coverUploadInput} type="file" accept="image/jpeg" hidden onChange={uploadCover} />
                  <MarkinaButton type="button" variant="secondary" onClick={() => coverUploadInput.current?.click()}>{currentCover ? "Substituir imagem de capa" : "Enviar imagem de capa"}</MarkinaButton>
                  {currentCover ? <div className={`cover-upload-current cover-upload-current--${currentCover.status}`} role="status"><strong>{currentCover.name}</strong><small>{currentCover.status === "ready" ? "Capa pronta para apresentação" : currentCover.status === "failed" ? currentCover.error ?? "O processamento falhou. Envie novamente esta capa ou escolha outro JPEG." : "Processando a capa"}</small></div> : <p className="gallery-scope-note">Nenhuma imagem de capa enviada ainda.</p>}
                  {detailsPollingError ? <div className="cover-upload-current cover-upload-current--failed" role="alert"><small>{detailsPollingError}</small><MarkinaButton type="button" variant="secondary" onClick={() => { setDetailsPollingError(""); setDetailsPollingRetry((value) => value + 1); }}>Atualizar estado da capa</MarkinaButton></div> : null}
                  <label>Tipografia do título<select name="cover_title_font" defaultValue={details?.settings?.cover_title_font ?? editor.gallery.cover_title_font}>{details?.font_options?.map((option) => <option key={option.token} value={option.token}>{option.label} · {option.category === "handwritten" ? "Manuscrita" : option.category === "editorial" ? "Editorial" : "Sem serifa"}</option>)}</select></label>
                  <label>Cor do título<input name="cover_title_color" type="color" defaultValue={editor.gallery.cover_title_color} /></label>
                  <label>Tamanho do título<input name="cover_title_size" type="number" min={12} max={96} defaultValue={editor.gallery.cover_title_size} /></label>
                  <label>Posição do título<select name="cover_title_position" defaultValue={editor.gallery.cover_title_position}><option value="top-left">Superior esquerdo</option><option value="top-center">Superior centro</option><option value="top-right">Superior direito</option><option value="middle-left">Centro esquerdo</option><option value="middle-center">Centro</option><option value="middle-right">Centro direito</option><option value="bottom-left">Inferior esquerdo</option><option value="bottom-center">Inferior centro</option><option value="bottom-right">Inferior direito</option></select></label>
                </fieldset>
              </div>
              <aside className="gallery-customization-preview" aria-live="polite">
                <p className="eyebrow">Prévia da capa</p>
                {coverPreviewUrl ? <div className="gallery-customization-preview-image"><img src={`/api${coverPreviewUrl}`} alt="Prévia da capa da galeria" /><strong className={`title-${visualPreview?.cover_title_position ?? "bottom-left"}`} style={{ color: visualPreview?.cover_title_color, fontFamily: titleFontFamily, fontSize: `${Math.min(visualPreview?.cover_title_size ?? 24, 34)}px` }}>{editor.gallery.name}</strong></div> : <div className="gallery-customization-preview-empty"><strong>Envie uma capa para visualizar o título</strong><span>A capa ficará sem marca-d’água e continuará fora das pastas de conteúdo.</span></div>}
              </aside>
            </div>
          </form>
        </section>
      ) : null}

      {currentStep === "imagens" ? (
        <section className="gallery-editor-panel">
          <div className="section-heading"><div><p className="eyebrow">Etapa 4</p><h2>Imagens e pastas</h2></div><StatusBadge>{folders.length} pasta(s)</StatusBadge></div>
          <p className="gallery-scope-note">Crie pastas e revise os JPEGs. Cada foto fica disponível automaticamente assim que sua prévia protegida termina de processar.</p>
          <div className="gallery-processing-default"><strong>Padrão da galeria</strong><p>Estes controles definem o comportamento herdado. Abra uma pasta abaixo para personalizar ou desligar seu processamento sem somar exposições.</p></div>
          <FacialPolicyPanel galleryId={sourceId} refreshToken={facialRefresh} />
          <PreviewAdjustmentPanel key={sourceId} galleryId={sourceId} />
          <fieldset className="gallery-organization-panel">
            <legend>Organização das pastas</legend>
            <label>Exibição das pastas<select aria-label="Exibição das pastas" value={visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode} onChange={saveFolderOrganization}><option value="individual">Pastas lado a lado</option><option value="sequential">Sequência cronológica</option></select></label>
            <div className={`gallery-organization-preview gallery-organization-preview--${visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode}`} aria-label={(visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode) === "sequential" ? "Prévia em sequência cronológica" : "Prévia com pastas lado a lado"}><span>1</span><span>2</span><span>3</span></div>
            <p>{(visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode) === "sequential" ? "A galeria percorre todas as pastas em sequência cronológica." : "A cliente escolhe uma pasta por vez para navegar."}</p>
          </fieldset>
          <form className="gallery-inline-form" onSubmit={createFolder}><label>Nome da nova pasta<input name="name" required placeholder="Ex.: Apresentação da manhã" /></label><MarkinaButton disabled={!editor.actions.can_create_folder}>Criar pasta</MarkinaButton></form>
          {folders.length ? <div className="gallery-folder-grid">{folders.map((folder) => <article key={folder.id} className={`${folderPublicationClass(folder)} ${folder.id === openFolderId ? "is-open" : ""}`}><button type="button" aria-label={`Abrir pasta ${folder.name}`} disabled={folderDeleteBusy} onClick={() => inspectFolder(folder.id)}><span className="gallery-folder-cover">{folder.preview_url ? <img src={`/api${folder.preview_url}`} alt="" /> : null}<b>{folder.photo_count ? `${folder.photo_count} fotos` : "Pasta vazia"}</b></span><strong>{folder.name}</strong><small>{folder.status === "released" ? "Disponível" : "Preparando prévias"}</small><FolderPublicationSummary folder={folder} /></button><div className="gallery-folder-actions">{folder.status === "preparing" ? <button type="button" className="link-button" disabled={folderDeleteBusy} onClick={() => { const name = window.prompt("Novo nome da pasta", folder.name); if (name) mutate(`/api/admin/photo-folders/${folder.id}`, "PATCH", { name }); }}>Renomear</button> : null}<button type="button" className="link-button danger-action" disabled={folderDeleteBusy || bulkDeleteBusy || uploadState.phase === "uploading"} onClick={() => deleteFolder(folder)} aria-label={`Excluir pasta ${folder.name}`}>{folderDeleteBusy ? "Excluindo…" : "Excluir pasta"}</button></div></article>)}</div> : <SystemState title="Nenhuma pasta nesta galeria" detail="Crie a primeira pasta para iniciar o carregamento das fotos." />}
          {selectedFolder ? (
            <div className="gallery-folder-workspace">
              <div className="section-heading"><div><p className="eyebrow">Pasta selecionada</p><h3>{selectedFolder.name}</h3></div><StatusBadge tone={selectedFolder.status === "released" ? "success" : "warning"}>{selectedFolder.status === "released" ? "Disponível" : "Preparando prévias"}</StatusBadge></div>
              <FolderProcessingPanel key={selectedFolder.id} folderId={selectedFolder.id} folderName={selectedFolder.name} />
              {uploadState.phase !== "idle" ? <div className={`upload-status upload-status--${uploadState.phase}`} role="status"><strong>{uploadState.phase === "uploading" ? `Enviando foto ${uploadState.current} de ${uploadState.total}` : uploadState.phase === "success" ? "Upload concluído" : "Falha no upload"}</strong>{uploadState.filename ? <span>{uploadState.filename}</span> : null}{uploadState.phase === "uploading" ? <progress value={uploadState.current} max={uploadState.total} /> : null}</div> : null}
              {photos.length ? <><div className="folder-photo-toolbar"><label><input type="checkbox" checked={photos.length > 0 && selectedPhotoIds.length === photos.length} disabled={bulkDeleteBusy} onChange={(event) => setSelectedPhotoIds(event.target.checked ? photos.map((photo) => photo.id) : [])} /> Selecionar todas</label><MarkinaButton type="button" className="mk-button--danger" disabled={bulkDeleteBusy || !selectedPhotoIds.some((id) => photos.some((photo) => photo.id === id && photo.can_delete))} onClick={deleteSelectedPhotos}>{bulkDeleteBusy ? "Excluindo…" : "Excluir selecionadas"}</MarkinaButton></div><div className="folder-photo-grid">{photos.map((photo) => <article key={photo.id} className={`photo-state-${photo.publication_state ?? "processing"}`}><label className="photo-select"><input type="checkbox" checked={selectedPhotoIds.includes(photo.id)} disabled={bulkDeleteBusy || !photo.can_delete} onChange={(event) => setSelectedPhotoIds((current) => event.target.checked ? [...current, photo.id] : current.filter((id) => id !== photo.id))} /> {photo.can_delete ? "Selecionar" : "Compra confirmada"}</label>{photo.preview_url ? <button type="button" className="photo-preview-button" onClick={() => setExpandedPhoto(photo)} aria-label={`Ampliar ${photo.name}`}><img src={`/api${photo.preview_url}`} alt={`Prévia com marca d’água de ${photo.name}`} /></button> : <div className="gallery-cover">Preparando prévia</div>}<strong>{photo.name}</strong><small>{photo.error ?? (photo.publication_state === "published" ? "Disponível" : photo.publication_state === "ready_to_publish" ? "Aguardando liberação automática" : photo.publication_state === "failed" ? "Falha no processamento" : "Preparando prévia")}</small><div className="photo-card-actions"><button type="button" className="link-button danger-action" disabled={bulkDeleteBusy || !photo.can_delete} title={photo.can_delete ? "Excluir foto" : "Há uma compra confirmada para esta foto"} onClick={() => deletePhoto(photo)}>{photo.can_delete ? "Excluir" : "Compra confirmada"}</button></div></article>)}</div></> : <SystemState title="Pasta sem fotos" detail="Selecione os JPEGs abaixo para iniciar o processamento." />}
              <form ref={uploadForm} className="gallery-inline-form" onSubmit={uploadPhotos}><input name="folder" type="hidden" value={selectedFolder.id} /><input ref={uploadInput} name="jpeg" type="file" accept="image/jpeg" multiple required hidden onChange={() => uploadForm.current?.requestSubmit()} /><MarkinaButton type="button" disabled={!editor.actions.can_upload} onClick={() => uploadInput.current?.click()}>Carregar fotos</MarkinaButton></form>
            </div>
          ) : null}
        </section>
      ) : null}

      {currentStep === "clientes" ? (
        <section className="gallery-editor-panel">
          <div className="section-heading"><div><p className="eyebrow">Etapa 5</p><h2>Clientes e acesso</h2></div><StatusBadge>{linkedClients.length} vínculo(s)</StatusBadge></div>
          <div className="unlisted-link"><span>Link permanente da Galeria pública</span><strong>{publicLink?.status === "active" ? "Ativo" : publicLink?.status === "legacy_unrecoverable" ? "Link legado indisponível" : "Ainda não disponível"}</strong>{publicLink?.link ? <input aria-label="Link da Galeria pública" readOnly value={publicLink.link} onFocus={(event) => event.currentTarget.select()} /> : null}<small>Este endereço permanece o mesmo enquanto a galeria existir. No primeiro acesso sem sessão válida, a cliente comprova o telefone por código.</small><div className="gallery-access-actions">{publicLink?.link ? <MarkinaButton type="button" variant="secondary" onClick={() => copyAccessLink(publicLink.link, "Link público")}>Copiar link</MarkinaButton> : publicLink?.status === "legacy_unrecoverable" ? <span>Solicite reparação administrativa somente em caso de incidente.</span> : <MarkinaButton type="button" disabled={Boolean(accessBusy)} onClick={createPublicLink}>Criar link permanente</MarkinaButton>}</div></div>
          <div className="gallery-client-grid">
            <section className="gallery-client-card" aria-labelledby="linked-clients-title">
              <p className="eyebrow">Acesso atual</p>
              <h3 id="linked-clients-title">Clientes vinculadas</h3>
              <p className="gallery-scope-note">Pessoas vinculadas a esta galeria. O acervo exclusivo de cada cliente fica no próprio card.</p>
              {unlinkTarget && (unlinkOperation || (unlinkError && !unlinkPreview)) ? <section className={`unlink-progress${unlinkError || unlinkOperation?.status === "failed" ? " unlink-progress--error" : ""}`} aria-label={`Desvinculação de ${unlinkTarget.name}`} aria-live="polite"><div><strong>{unlinkOperation?.progress.label ?? "Não foi possível desvincular"}</strong>{unlinkOperation ? <span>{unlinkOperation.progress.percent}%</span> : null}</div>{unlinkOperation ? <progress value={unlinkOperation.progress.percent} max={100} /> : null}<p>{unlinkError || unlinkOperation?.last_error || (unlinkOperation?.status === "completed" ? "Cliente desvinculada. Cadastro e histórico foram preservados." : unlinkOperation?.status === "cancelled" ? "Desvinculação cancelada antes da remoção física." : "A desvinculação continua em segundo plano.")}</p><div>{unlinkOperation?.actions.can_cancel ? <MarkinaButton type="button" variant="secondary" disabled={unlinkBusy} onClick={() => unlinkOperationAction("cancel")}>Cancelar desvinculação</MarkinaButton> : null}{unlinkOperation?.actions.can_retry ? <MarkinaButton type="button" disabled={unlinkBusy} onClick={() => unlinkOperationAction("retry")}>Retomar desvinculação</MarkinaButton> : null}{!unlinkOperation?.actions.should_poll ? <MarkinaButton type="button" variant="secondary" onClick={() => { setUnlinkOperation(null); setUnlinkTarget(null); setUnlinkError(""); }}>Fechar</MarkinaButton> : null}</div></section> : null}
              {linkedClients.length ? (
                <div className="gallery-linked-clients" aria-label="Lista de clientes vinculadas">
                  {linkedClients.map((person) => <ClientGalleryCard key={person.client_id} person={person} parentGalleryId={sourceId} linkedClients={linkedClients} onRefresh={() => setRefresh((value) => value + 1)} actions={<><MarkinaButton type="button" variant="secondary" className="gallery-client-unlink" disabled={unlinkBusy || Boolean(unlinkOperation?.actions.should_poll)} onClick={() => openUnlinkConfirmation(person)}>Desvincular cliente</MarkinaButton></>} />)}
                </div>
              ) : <SystemState title="Nenhuma cliente vinculada" detail="Use a busca ou o novo cadastro para criar o primeiro vínculo." />}
            </section>
            <section className="gallery-client-card" aria-labelledby="existing-client-title">
              <p className="eyebrow">Cadastro existente</p>
              <h3 id="existing-client-title">Vincular cliente</h3>
              <label className="gallery-client-search">Buscar por nome ou WhatsApp<input value={clientQuery} onChange={(event) => setClientQuery(event.target.value)} placeholder="Ex.: Ana ou 11999999999" /></label>
              {clientOptions.length ? <div className="client-option-list">{clientOptions.map((option) => {
                const linked = linkedClients.some((person) => person.client_id === option.id);
                return <div className="client-option-row" key={option.id}><span><strong>{option.name}</strong><small>{option.phone}</small></span><div className="client-option-actions">{linked ? <StatusBadge tone="success">Já vinculada</StatusBadge> : <button type="button" className="client-option-action" aria-label={`Vincular ${option.name}`} onClick={() => bindClient(option.id, option.name)}>Vincular</button>}<button type="button" className="client-option-edit" aria-label={`Editar cadastro de ${option.name}`} onClick={() => setClientEditTarget(option)}>Editar</button></div></div>;
              })}</div> : <SystemState title="Nenhum cadastro encontrado" detail="Revise a busca ou use o bloco Novo cadastro." />}
            </section>
            <section className="gallery-client-card" aria-labelledby="new-client-title">
              <p className="eyebrow">Novo cadastro</p>
              <h3 id="new-client-title">Cadastrar e vincular</h3>
              <p className="gallery-scope-note">Crie o cadastro somente quando a cliente ainda não aparecer na busca.</p>
              <ClientCreateForm onCreated={(created) => bindClient(created.id, created.name)} />
            </section>
          </div>
        </section>
      ) : null}

      {expandedPhoto ? <div className="photo-preview-dialog" role="presentation" onMouseDown={() => setExpandedPhoto(null)}><div ref={previewDialog} role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${expandedPhoto.name}`} tabIndex={-1} onKeyDown={(event) => { if (event.key === "Escape") setExpandedPhoto(null); }} onMouseDown={(event) => event.stopPropagation()}><button type="button" className="photo-preview-close" onClick={() => setExpandedPhoto(null)}>Fechar</button><img src={`/api${expandedPhoto.preview_url}`} alt={`Prévia com marca d’água ampliada de ${expandedPhoto.name}`} /><p>{expandedPhoto.name}</p></div></div> : null}
      {clientEditTarget ? <ClientEditorDialog key={clientEditTarget.id} client={clientEditTarget} onClose={() => setClientEditTarget(null)} onUpdated={(updated) => { setClientOptions((current) => current.map((item) => item.id === updated.id ? updated : item)); setClientEditTarget(null); setMessage("Cadastro da cliente atualizado sem alterar seus vínculos ou histórico."); setRefresh((value) => value + 1); }} onDeleted={(clientId) => { setClientOptions((current) => current.filter((item) => item.id !== clientId)); setClientEditTarget(null); setMessage("Cadastro e estado operacional excluídos."); setRefresh((value) => value + 1); }} /> : null}
      {unlinkPreview ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="unlink-client-title" aria-modal="true" className="mk-dialog" role="dialog"><p className="eyebrow">Desvinculação da Galeria pública</p><h2 id="unlink-client-title">Desvincular {unlinkPreview.target.client_name}?</h2><p>O acesso desta cliente será encerrado nesta Galeria pública e na privada associada. O cadastro, as outras galerias e todo histórico comercial serão preservados; o acervo privado compartilhado permanece para os demais membros.</p><div className="unlink-summary"><span><strong>{unlinkPreview.inventory.remove.memberships ?? 0}</strong> vínculo privado</span><span><strong>{unlinkPreview.inventory.remove.selections ?? 0}</strong> selecionadas removíveis</span><span><strong>{typeof unlinkPreview.inventory.preserve.orders === "number" ? unlinkPreview.inventory.preserve.orders : 0}</strong> pedidos preservados</span><span><strong>{typeof unlinkPreview.inventory.preserve.available_references === "number" ? unlinkPreview.inventory.preserve.available_references : 0}</strong> fotos preservadas</span></div><p>Um pagamento informado e ainda em análise impede a desvinculação até a decisão administrativa.</p>{unlinkError ? <p className="form-message form-message--error" role="alert">{unlinkError}</p> : null}<div className="mk-dialog__actions"><MarkinaButton type="button" variant="secondary" disabled={unlinkBusy} onClick={() => { setUnlinkPreview(null); setUnlinkTarget(null); setUnlinkError(""); }}>Cancelar</MarkinaButton><MarkinaButton type="button" className="mk-button--danger" disabled={unlinkBusy} onClick={confirmUnlink}>{unlinkBusy ? "Iniciando…" : "Confirmar desvinculação"}</MarkinaButton></div></section></div> : null}
      {message ? <p className="notice" role="status">{message}</p> : null}
      <footer className="gallery-editor-footer">
        {previous ? <Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${sourceId}/edit/${previous}`} onClick={confirmDiscard}>← Voltar</Link> : <span />}
      {next && activeEditableForm ? <MarkinaButton type="submit" form={activeEditableForm} disabled={savingStep || (currentStep === "detalhes" && !coverReady)}>{savingStep ? "Salvando…" : "Salvar e avançar →"}</MarkinaButton> : currentStep === "imagens" ? <MarkinaButton type="button" disabled={savingStep} onClick={saveImagesAndAdvance}>{savingStep ? "Salvando…" : "Salvar e avançar →"}</MarkinaButton> : next ? <Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}/edit/${next}`}>Avançar →</Link> : <MarkinaButton type="button" disabled={savingStep} onClick={completeGallery}>{savingStep ? "Verificando…" : "Concluir"}</MarkinaButton>}
      </footer>
    </main>
  );
}
