"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ChangeEvent, type FormEvent, type MouseEvent, useEffect, useMemo, useRef, useState } from "react";

import { MarkinaButton, StatusBadge, SystemState } from "../../../../../ui-kit";
import { ClientGalleryCard, type ClientGalleryRow } from "../../../client-gallery-card";
import { formatBrazilianCurrency, maskBrazilianCurrencyInput, parseBrazilianCurrency, type PriceTier } from "../../../pricing-rules";

type StepId = "ajustes" | "vendas" | "detalhes" | "imagens" | "clientes";
type EditorStep = { id: StepId; label: string; status: "complete" | "pending" | "unavailable"; available: boolean };
type Editor = { gallery: { id: string; name: string; event_name: string; description: string; active: boolean; access_mode: "standard" | "invite_only" | "collective_protected"; unlisted_link: string | null; public_link?: { status: string; capability_id: string | null; expires_at: string | null; secret_available: boolean }; cover_photo_id: string | null; cover_preview_url: string | null; folder_display_mode: string; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string }; steps: EditorStep[]; counts: { folders: number; registrations: number; derived_galleries: number }; capabilities: Record<string, boolean>; actions: { can_create_folder: boolean; can_upload: boolean } };
type PublicationCounts = { published: number; ready_to_publish: number; processing: number; failed: number };
type Folder = { id: string; name: string; status: string; position: number; photo_count: number; preview_url: string | null; released_at: string | null; publication_counts?: PublicationCounts };
type Photo = { id: string; name: string; preview_url: string | null; status: string; publication_state?: "published" | "ready_to_publish" | "processing" | "failed"; available?: boolean; width?: number | null; height?: number | null; error: string | null; can_delete: boolean; is_cover: boolean };
type AvailablePhoto = { id: string; name: string; folder_name: string; preview_url: string | null; width?: number | null; height?: number | null };
type ClientRow = ClientGalleryRow;
type ClientOption = { id: string; name: string; phone: string };
type ClientDeletionInventory = { client_id: string; blockers: Record<string, number>; blocking: Record<string, number>; can_delete: boolean; removable: { client: number; phone_records: number } };
type PricingMode = "fixed" | "progressive" | "legacy_volume";
type PricingPreset = { id: string; code: string; name: string; label: string; version: number; active: boolean; tiers: PriceTier[] };
type PricingQuote = { quantity: number; parcels: Array<PriceTier & { quantity: number; subtotal_cents: number }>; base_total_cents: number; savings_cents: number; total_cents: number };
type SalesData = { available: boolean; reason?: string; capabilities: string[]; pricing_mode: PricingMode; fixed_unit_price_cents: number | null; progressive_pricing_preset_id: string | null; pricing_snapshot: Record<string, unknown> | null; pricing_review_required: boolean; tiers: PriceTier[]; pix: { copy_paste: string | null; input_type: "br_code" | "cpf" | "phone" | "email" | null; receiver_name: string | null; receiver_city: string | null; qr_code_payload: null; qr_png_data_url: string | null; review_required: boolean; instructions: string | null }; sales_message: string; selection_duration_days: number | null; favorites_enabled: boolean; comments_enabled: boolean };
type GalleryLink = { status: "active" | "unavailable" | "legacy_unrecoverable"; capability_id: string | null; expires_at: string | null; secret_available: boolean; link: string | null };
type PrivateMember = { membership_id: string; client_id: string; client_name: string; phone_e164: string | null; status: "active" | "blocked" | "unlinked"; selected_count: number; purchased_count: number; order_count: number; confirmed_total_cents: number; payment_status: "none" | "pending" | "confirmed" };
type PrivateAccessState = { loading: boolean; error: string | null; link: GalleryLink | null; members: PrivateMember[] };
type FontOption = { token: string; label: string; category: "sans" | "editorial" | "handwritten"; css_family: string };
type CoverOption = { id: string; name: string; source: "content" | "cover_assets"; status: "ready" | "processing"; preview_url: string | null; width: number | null; height: number | null };
type DetailsData = { available: boolean; capabilities: string[]; font_options: FontOption[]; cover_options: CoverOption[]; settings: { cover_photo_id: string | null; cover_preview_url: string | null; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string } };
const clientBlockerLabels: Record<string, string> = {
  gallery_accesses: "acessos",
  public_gallery_registrations: "vínculos públicos",
  private_galleries_owned: "galerias privadas",
  private_gallery_memberships: "vínculos privados",
  gallery_capabilities: "convites e links",
  selections: "seleções",
  favorites: "favoritos",
  views: "visualizações",
  comments: "comentários",
  orders: "pedidos",
  payment_communications: "comunicações de pagamento",
  membership_notifications: "notificações",
  sessions: "sessões",
  otp_challenges: "validações OTP",
  whatsapp_deliveries: "mensagens WhatsApp",
};
type VisualPreview = { folder_display_mode: string; cover_title_font: string; cover_title_color: string; cover_title_size: number; cover_title_position: string };
type UnlinkPreview = { operation_type: "unlink_client"; target: { parent_gallery_id: string; parent_gallery_name: string; client_id: string; client_name: string }; inventory: { remove: Record<string, number>; preserve: Record<string, number | Record<string, number>> }; consequences: { gallery_relationship_removed: boolean; private_gallery_removed: boolean; client_preserved: boolean; commercial_history_preserved: boolean; other_gallery_relationships_preserved: boolean; restoration_available_after_start: boolean } };
type LifecycleOperation = { operation_id: string; status: string; status_url: string; last_error: string | null; progress: { label: string; percent: number; failed_step: string | null }; actions: { can_cancel: boolean; can_retry: boolean; should_poll: boolean; poll_after_ms: number | null } };

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
    <small className="is-published">{counts.published} publicadas</small>
    <small className="is-ready">{counts.ready_to_publish} prontas</small>
    <small className="is-processing">{counts.processing} processando</small>
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
  return response.status === 204 ? null : response.json();
}

export default function GalleryEditor({ sourceId, step, initialFolderId = "" }: { sourceId: string; step: string; initialFolderId?: string }) {
  const router = useRouter();
  const currentStep = step as StepId;
  const [editor, setEditor] = useState<Editor | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [availablePhotos, setAvailablePhotos] = useState<AvailablePhoto[]>([]);
  const [selectedPhotoIds, setSelectedPhotoIds] = useState<string[]>([]);
  const [expandedPhoto, setExpandedPhoto] = useState<Photo | null>(null);
  const [openFolderId, setOpenFolderId] = useState("");
  const [linkedClients, setLinkedClients] = useState<ClientRow[]>([]);
  const [clientOptions, setClientOptions] = useState<ClientOption[]>([]);
  const [clientQuery, setClientQuery] = useState("");
  const [clientEditTarget, setClientEditTarget] = useState<ClientOption | null>(null);
  const [clientEditName, setClientEditName] = useState("");
  const [clientEditPhone, setClientEditPhone] = useState("");
  const [clientEditChallengeId, setClientEditChallengeId] = useState("");
  const [clientEditOtp, setClientEditOtp] = useState("");
  const [clientEditBusy, setClientEditBusy] = useState(false);
  const [clientEditError, setClientEditError] = useState("");
  const [clientDeletionInventory, setClientDeletionInventory] = useState<ClientDeletionInventory | null>(null);
  const [sales, setSales] = useState<SalesData | null>(null);
  const [salesError, setSalesError] = useState("");
  const [pricingPresets, setPricingPresets] = useState<PricingPreset[]>([]);
  const [fixedPriceInput, setFixedPriceInput] = useState("R$ 0,00");
  const [quoteQuantity, setQuoteQuantity] = useState(60);
  const [pricingQuote, setPricingQuote] = useState<PricingQuote | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [confirmLegacyConversion, setConfirmLegacyConversion] = useState(false);
  const [publicLink, setPublicLink] = useState<GalleryLink | null>(null);
  const [privateAccess, setPrivateAccess] = useState<Record<string, PrivateAccessState>>({});
  const [memberCandidateByGallery, setMemberCandidateByGallery] = useState<Record<string, string>>({});
  const [accessBusy, setAccessBusy] = useState("");
  const [dirty, setDirty] = useState(false);
  const [savingStep, setSavingStep] = useState(false);
  const [details, setDetails] = useState<DetailsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [uploadState, setUploadState] = useState<{ phase: "idle" | "uploading" | "success" | "error"; current: number; total: number; filename?: string }>({ phase: "idle", current: 0, total: 0 });
  const [failed, setFailed] = useState(false);
  const [visualPreview, setVisualPreview] = useState<VisualPreview | null>(null);
  const [unlinkPreview, setUnlinkPreview] = useState<UnlinkPreview | null>(null);
  const [unlinkOperation, setUnlinkOperation] = useState<LifecycleOperation | null>(null);
  const [unlinkBusy, setUnlinkBusy] = useState(false);
  const [unlinkTarget, setUnlinkTarget] = useState<{ clientId: string; name: string } | null>(null);
  const [unlinkError, setUnlinkError] = useState("");
  const [privateTarget, setPrivateTarget] = useState<ClientRow | null>(null);
  const [adminPhotoIds, setAdminPhotoIds] = useState<string[]>([]);
  const [privateActionBusy, setPrivateActionBusy] = useState(false);
  const [privateActionError, setPrivateActionError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const previewDialog = useRef<HTMLDivElement>(null);
  const uploadInput = useRef<HTMLInputElement>(null);
  const coverUploadInput = useRef<HTMLInputElement>(null);
  const uploadForm = useRef<HTMLFormElement>(null);
  const unlinkIdempotencyKey = useRef("");

  useEffect(() => {
    if (expandedPhoto) previewDialog.current?.focus();
  }, [expandedPhoto]);

  useEffect(() => {
    if (!dirty) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [dirty]);

  useEffect(() => {
    if (currentStep !== "detalhes" || !details?.cover_options?.some((option) => option.status === "processing")) return;
    const timer = window.setTimeout(() => setRefresh((value) => value + 1), 1500);
    return () => window.clearTimeout(timer);
  }, [currentStep, details]);

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
    if (currentStep !== "clientes") return;
    const galleryIds = [...new Set(linkedClients.map((client) => client.derived_gallery_id).filter((id): id is string => Boolean(id)))];
    let active = true;
    if (!galleryIds.length) {
      queueMicrotask(() => { if (active) setPrivateAccess({}); });
      return () => { active = false; };
    }
    queueMicrotask(() => {
      if (active) setPrivateAccess((current) => Object.fromEntries(galleryIds.map((galleryId) => [galleryId, { loading: true, error: null, link: current[galleryId]?.link ?? null, members: current[galleryId]?.members ?? [] }])));
    });
    Promise.all(galleryIds.map(async (galleryId) => {
      try {
        const [link, members] = await Promise.all([
          jsonRequest(`/api/admin/derived-galleries/${galleryId}/link`) as Promise<GalleryLink>,
          jsonRequest(`/api/admin/derived-galleries/${galleryId}/members`) as Promise<{ members: PrivateMember[] }>,
        ]);
        return [galleryId, { loading: false, error: null, link, members: members.members ?? [] }] as const;
      } catch (error) {
        return [galleryId, { loading: false, error: error instanceof Error ? error.message : "Não foi possível carregar a galeria privada.", link: null, members: [] }] as const;
      }
    })).then((entries) => { if (active) setPrivateAccess(Object.fromEntries(entries)); });
    return () => { active = false; };
  }, [currentStep, linkedClients]);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setLoading(true);
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
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/available-photos`),
      jsonRequest(`/api/admin/parent-galleries/${sourceId}/public-link`),
    ]);
    Promise.all([editorRequest, sectionRequest])
      .then(([editorData, sectionData]) => {
        if (!active) return;
        setEditor(editorData as Editor);
        const visual = (editorData as Editor).gallery;
        setVisualPreview({ folder_display_mode: visual.folder_display_mode ?? "individual", cover_title_font: visual.cover_title_font ?? "system-sans", cover_title_color: visual.cover_title_color ?? "#FFFFFF", cover_title_size: visual.cover_title_size ?? 32, cover_title_position: visual.cover_title_position ?? "bottom-left" });
        if (currentStep === "vendas") {
          const [salesData, presetData] = sectionData as [SalesData, { presets: PricingPreset[] }];
          setSales(salesData);
          setSalesError("");
          setPricingPresets(presetData.presets ?? []);
          setFixedPriceInput(formatBrazilianCurrency(salesData.fixed_unit_price_cents ?? salesData.tiers?.[0]?.unit_price_cents ?? 0));
          setConfirmLegacyConversion(false);
          setPricingQuote(null);
        }
        if (currentStep === "detalhes") setDetails(sectionData as DetailsData);
        if (currentStep === "imagens") {
          const folderData = sectionData as { folders: Folder[] };
          setFolders(folderData.folders ?? []);
          const requested = initialFolderId && folderData.folders?.some((folder) => folder.id === initialFolderId) ? initialFolderId : "";
          if (requested) queueMicrotask(() => inspectFolder(requested));
        }
        if (currentStep === "clientes") {
          const [clientData, optionData, photoData, linkData] = sectionData as [{ clients: ClientRow[] }, { clients: ClientOption[] }, { photos: AvailablePhoto[] }, GalleryLink];
          setLinkedClients(clientData.clients ?? []);
          setClientOptions(optionData.clients ?? []);
          setAvailablePhotos(photoData.photos ?? []);
          setPublicLink(linkData);
        }
      })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [clientQuery, currentStep, initialFolderId, refresh, sourceId]);

  const currentIndex = stepOrder.indexOf(currentStep);
  const previous = currentIndex > 0 ? stepOrder[currentIndex - 1] : null;
  const next = currentIndex < stepOrder.length - 1 ? stepOrder[currentIndex + 1] : null;
  const selectedFolder = useMemo(
    () => folders.find((folder) => folder.id === openFolderId) ?? null,
    [folders, openFolderId],
  );
  const coverPreviewUrl = details?.cover_options?.find((option) => option.id === details.settings?.cover_photo_id)?.preview_url ?? details?.settings?.cover_preview_url ?? editor?.gallery.cover_preview_url ?? null;
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

  async function setCover(photo: Photo) {
    try {
      await jsonRequest(`/api/admin/parent-galleries/${sourceId}/cover`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ photo_id: photo.id }),
      });
      setPhotos((current) => current.map((item) => ({ ...item, is_cover: item.id === photo.id })));
      setMessage("Foto definida como capa da galeria.");
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível definir a capa.");
    }
  }

  async function deletePhoto(photo: Photo) {
    if (!window.confirm(`Excluir ${photo.name}? Esta ação não pode ser desfeita.`)) return;
    try {
      await jsonRequest(`/api/admin/photo-folders/${openFolderId}/photos/${photo.id}`, { method: "DELETE" });
      setMessage("Foto excluída da pasta.");
      setExpandedPhoto(null);
      await inspectFolder(openFolderId);
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível excluir a foto.");
    }
  }

  async function deleteSelectedPhotos() {
    const eligible = photos.filter((photo) => selectedPhotoIds.includes(photo.id) && photo.can_delete);
    if (!eligible.length) return;
    if (!window.confirm(`Excluir ${eligible.length} foto(s) selecionada(s)? Esta ação não pode ser desfeita.`)) return;
    try {
      const result = await jsonRequest(`/api/admin/photo-folders/${openFolderId}/photos`, {
        method: "DELETE",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ photo_ids: selectedPhotoIds }),
      });
      const blockedCount = result.blocked_ids?.length ?? 0;
      setMessage(blockedCount ? `${result.deleted_ids.length} foto(s) excluída(s); ${blockedCount} protegida(s) por compra confirmada.` : `${result.deleted_ids.length} foto(s) excluída(s).`);
      setSelectedPhotoIds([]);
      await inspectFolder(openFolderId);
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível excluir as fotos.");
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
      access_mode: form.get("access_mode"),
    });
    if (saved) advanceAfterSave();
    setSavingStep(false);
  }

  async function saveVisualSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savingStep) return;
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

  async function saveSales(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sales || savingStep) return;
    setSalesError("");
    if (sales.pricing_mode === "legacy_volume") {
      setSalesError("Escolha preço fixo ou uma tabela progressiva para converter a configuração legada.");
      return;
    }
    const fixedUnitPriceCents = sales.pricing_mode === "fixed"
      ? parseBrazilianCurrency(fixedPriceInput)
      : null;
    if (sales.pricing_mode === "fixed" && fixedUnitPriceCents === null) {
      setSalesError("Informe o valor unitário como moeda brasileira, por exemplo R$ 7,00.");
      return;
    }
    if (sales.pricing_mode === "progressive" && !sales.progressive_pricing_preset_id) {
      setSalesError("Escolha uma tabela global de preço progressivo.");
      return;
    }
    const pixCopyPaste = sales.pix.copy_paste?.trim() || null;
    const usesSimplePixKey = Boolean(pixCopyPaste && !pixCopyPaste.startsWith("000201"));
    if (usesSimplePixKey && (!sales.pix.receiver_name?.trim() || !sales.pix.receiver_city?.trim())) {
      setSalesError("Para gerar o QR a partir de uma chave, informe o nome e a cidade do recebedor.");
      return;
    }
    setSavingStep(true);
    try {
      const saved = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/sales`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          pricing_mode: sales.pricing_mode,
          fixed_unit_price_cents: fixedUnitPriceCents,
          progressive_pricing_preset_id: sales.pricing_mode === "progressive" ? sales.progressive_pricing_preset_id : null,
          confirm_legacy_conversion: confirmLegacyConversion,
          pix: {
            copy_paste: pixCopyPaste,
            receiver_name: usesSimplePixKey ? sales.pix.receiver_name : null,
            receiver_city: usesSimplePixKey ? sales.pix.receiver_city : null,
            instructions: sales.pix.instructions,
          },
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

  async function changePublicLink(action: "create" | "rotate") {
    if (accessBusy) return;
    setAccessBusy(`public-${action}`);
    try {
      const path = action === "rotate"
        ? `/api/admin/parent-galleries/${sourceId}/public-link/rotate`
        : `/api/admin/parent-galleries/${sourceId}/public-link`;
      const result = await jsonRequest(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      }) as GalleryLink;
      setPublicLink(result);
      setMessage(action === "rotate" ? "Link público regenerado; o endereço anterior foi revogado." : "Link público criado.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atualizar o link público.");
    } finally {
      setAccessBusy("");
    }
  }

  async function changePrivateLink(galleryId: string, action: "create" | "rotate") {
    if (accessBusy) return;
    setAccessBusy(`${galleryId}-${action}`);
    try {
      const suffix = action === "rotate" ? "/rotate" : "";
      const result = await jsonRequest(`/api/admin/derived-galleries/${galleryId}/link${suffix}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      }) as GalleryLink;
      setPrivateAccess((current) => ({ ...current, [galleryId]: { ...current[galleryId], link: result } }));
      setMessage(action === "rotate" ? "Link privado regenerado; o endereço anterior foi revogado." : "Link privado criado.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atualizar o link privado.");
    } finally {
      setAccessBusy("");
    }
  }

  async function addPrivateMember(galleryId: string) {
    const clientId = memberCandidateByGallery[galleryId];
    if (!clientId || accessBusy) return;
    setAccessBusy(`${galleryId}-member-add`);
    try {
      await jsonRequest(`/api/admin/derived-galleries/${galleryId}/members`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ client_id: clientId }),
      });
      setMessage("Cliente adicionada à galeria privada.");
      setMemberCandidateByGallery((current) => ({ ...current, [galleryId]: "" }));
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível adicionar a cliente.");
    } finally {
      setAccessBusy("");
    }
  }

  async function changePrivateMember(galleryId: string, member: PrivateMember, action: "block" | "unblock" | "unlink") {
    if (accessBusy) return;
    if (action === "unlink" && !window.confirm(`Desvincular ${member.client_name} desta galeria privada? O cadastro e o histórico serão preservados.`)) return;
    setAccessBusy(`${galleryId}-${member.client_id}-${action}`);
    try {
      const suffix = action === "unlink" ? "" : `/${action}`;
      await jsonRequest(`/api/admin/derived-galleries/${galleryId}/members/${member.client_id}${suffix}`, {
        method: action === "unlink" ? "DELETE" : "POST",
      });
      setMessage(action === "block" ? "Acesso da cliente bloqueado." : action === "unblock" ? "Acesso da cliente desbloqueado." : "Cliente desvinculada sem apagar seu histórico.");
      setRefresh((value) => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível atualizar a cliente.");
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
      setMessage("Capa enviada para processamento. As opções serão atualizadas automaticamente.");
      setRefresh((value) => value + 1);
    } catch (error) {
      setUploadState({ phase: "error", current: 0, total: 1, filename: file.name });
      setMessage(error instanceof Error ? error.message : "Não foi possível enviar a capa.");
    } finally {
      event.target.value = "";
    }
  }

  async function setCoverOption(option: CoverOption) {
    const result = await mutate(`/api/admin/parent-galleries/${sourceId}/cover`, "PUT", { photo_id: option.id });
    if (result) setMessage("Capa atualizada na prévia protegida.");
  }

  async function publishFolder(folderId: string) {
    const result = await mutate(`/api/admin/photo-folders/${folderId}/publish`, "POST", {});
    if (!result) return;
    setMessage(`${result.published_count} foto(s) publicada(s); ${result.pending_count} em processamento e ${result.failed_count} com falha.`);
    await inspectFolder(folderId);
  }

  async function publishReadyAndAdvance() {
    if (savingStep) return;
    setSavingStep(true);
    try {
      const result = await jsonRequest(`/api/admin/parent-galleries/${sourceId}/publish-ready`, {
        method: "POST",
      }) as { published_count: number; pending_count: number; failed_count: number; available_count: number };
      if (result.pending_count || result.failed_count) {
        setMessage(`${result.published_count} foto(s) pronta(s) publicada(s). Ainda há ${result.pending_count} em processamento e ${result.failed_count} com falha; revise a etapa antes de avançar.`);
        setRefresh((value) => value + 1);
        return;
      }
      setMessage(`${result.available_count} foto(s) publicadas na Galeria pública.`);
      advanceAfterSave();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível publicar as fotos prontas.");
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
      const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "-");
      try {
        const photo = await jsonRequest(`/api/admin/photo-folders/${folderId}/photos`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            storage_key: `${sourceId}/${folderId}/${Date.now()}-${index}-${safeName}`,
          }),
        });
        await jsonRequest(`/api/admin/photo-assets/${photo.id}/source`, {
          method: "PUT",
          headers: { "content-type": "image/jpeg" },
          body: file,
        });
      } catch (error) {
        setUploadState({ phase: "error", current: index, total: files.length, filename: file.name });
        setMessage(error instanceof Error ? error.message : `Falha ao enviar ${file.name}.`);
        return;
      }
    }
    setUploadState({ phase: "success", current: files.length, total: files.length });
    setMessage(`${files.length} foto(s) enviada(s) para processamento.`);
    setRefresh((value) => value + 1);
    await inspectFolder(folderId);
    formElement.reset();
  }

  async function createClientAndGallery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("full_name") ?? "");
    const created = await mutate("/api/admin/clients", "POST", {
      full_name: name,
      phone_e164: form.get("phone_e164"),
    });
    if (!created) return;
    await bindClient(created.id, name);
    formElement.reset();
  }

  async function bindClient(clientId: string, name: string) {
    await mutate("/api/admin/derived-galleries", "POST", {
      parent_gallery_id: sourceId,
      client_id: clientId,
      name: `${editor?.gallery.name ?? "Galeria"} · ${name}`,
      photo_ids: [],
    });
  }

  function openClientEditor(option: ClientOption) {
    setClientEditTarget(option);
    setClientEditName(option.name);
    setClientEditPhone(option.phone);
    setClientEditChallengeId("");
    setClientEditOtp("");
    setClientEditError("");
    setClientDeletionInventory(null);
  }

  function closeClientEditor() {
    if (clientEditBusy) return;
    setClientEditTarget(null);
    setClientDeletionInventory(null);
    setClientEditError("");
  }

  async function saveClient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!clientEditTarget || clientEditBusy) return;
    setClientEditBusy(true);
    setClientEditError("");
    try {
      const phoneChanged = clientEditPhone.trim() !== clientEditTarget.phone;
      if (phoneChanged && !clientEditChallengeId) {
        const challenge = await jsonRequest("/api/auth/client/challenge", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ full_name: clientEditName, phone: clientEditPhone }),
        }) as { challenge_id: string };
        setClientEditChallengeId(challenge.challenge_id);
        setMessage("Código enviado ao novo WhatsApp. Informe-o para concluir a troca.");
        return;
      }
      if (phoneChanged) {
        await jsonRequest(`/api/admin/clients/${clientEditTarget.id}/phone`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            phone_e164: clientEditPhone,
            challenge_id: clientEditChallengeId,
            code: clientEditOtp,
          }),
        });
      }
      if (clientEditName.trim() !== clientEditTarget.name) {
        await jsonRequest(`/api/admin/clients/${clientEditTarget.id}`, {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ full_name: clientEditName }),
        });
      }
      setMessage("Cadastro da cliente atualizado sem alterar seus vínculos ou histórico.");
      setClientEditTarget(null);
      setClientDeletionInventory(null);
      setRefresh((value) => value + 1);
    } catch (error) {
      setClientEditError(error instanceof Error ? error.message : "Não foi possível atualizar a cliente.");
    } finally {
      setClientEditBusy(false);
    }
  }

  async function inspectClientDeletion() {
    if (!clientEditTarget || clientEditBusy) return;
    setClientEditBusy(true);
    setClientEditError("");
    try {
      const inventory = await jsonRequest(`/api/admin/clients/${clientEditTarget.id}/deletion-inventory`) as ClientDeletionInventory;
      setClientDeletionInventory(inventory);
    } catch (error) {
      setClientEditError(error instanceof Error ? error.message : "Não foi possível verificar a exclusão.");
    } finally {
      setClientEditBusy(false);
    }
  }

  async function confirmClientDeletion() {
    if (!clientEditTarget || !clientDeletionInventory?.can_delete || clientEditBusy) return;
    setClientEditBusy(true);
    setClientEditError("");
    try {
      await jsonRequest(`/api/admin/clients/${clientEditTarget.id}`, { method: "DELETE" });
      setMessage("Cadastro sem histórico excluído.");
      setClientEditTarget(null);
      setClientDeletionInventory(null);
      setRefresh((value) => value + 1);
    } catch (error) {
      setClientEditError(error instanceof Error ? error.message : "Não foi possível excluir a cliente.");
    } finally {
      setClientEditBusy(false);
    }
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

  async function createAdministrativePrivateGallery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!privateTarget || !adminPhotoIds.length || privateActionBusy) return;
    setPrivateActionBusy(true);
    setPrivateActionError("");
    try {
      await jsonRequest("/api/admin/derived-galleries", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          parent_gallery_id: sourceId,
          client_id: privateTarget.client_id,
          name: `${editor?.gallery.name ?? "Galeria"} · ${privateTarget.name}`,
          photo_ids: adminPhotoIds,
        }),
      });
      setMessage(`Galeria privada de ${privateTarget.name} salva com ${adminPhotoIds.length} foto(s) disponível(is), sem seleção automática.`);
      setPrivateTarget(null);
      setAdminPhotoIds([]);
      setRefresh((value) => value + 1);
    } catch (error) {
      setPrivateActionError(error instanceof Error ? error.message : "Não foi possível disponibilizar as fotos.");
    } finally {
      setPrivateActionBusy(false);
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
          <label>Modo de acesso<select name="access_mode" defaultValue={editor.gallery.access_mode}><option value="standard">Padrão — link + OTP libera a navegação</option><option value="invite_only">Somente convite individual</option><option value="collective_protected">Coletivo protegido — sem grade pública</option></select><small className="field-hint">A autorização é aplicada pelo backend; nenhuma opção libera prévias antes do login.</small></label>
          <div className="access-mode-hints" role="region" aria-label="Como funcionam os modos de acesso"><article><strong>Padrão</strong><p>Quem recebe o link fixo e conclui o OTP entra na Galeria pública e pode iniciar sua seleção.</p></article><article><strong>Somente convite individual</strong><p>O link público não cadastra novas pessoas. Apenas clientes já vinculadas pelo fotógrafo ou por convite individual autorizado acessam a galeria.</p></article><article><strong>Coletivo protegido</strong><p>O link e o OTP registram uma solicitação pendente, mas nunca mostram a grade coletiva. Este modo não ativa reconhecimento facial.</p></article></div>
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
                <p>Escolha um valor fixo para qualquer quantidade ou aplique uma tabela progressiva cadastrada globalmente. Pedidos existentes não são recalculados.</p>
                {sales.pricing_review_required || sales.pricing_mode === "legacy_volume" ? <div className="notice" role="alert"><strong>Configuração legada precisa de revisão.</strong><span>As faixas antigas não serão convertidas automaticamente. Escolha um dos modos abaixo e confirme a conversão.</span></div> : null}
                <div className="gallery-pricing-mode" role="radiogroup" aria-label="Modo de preço">
                  <label><input type="radio" name="pricing_mode" value="fixed" checked={sales.pricing_mode === "fixed"} onChange={() => { setSales((current) => current ? { ...current, pricing_mode: "fixed", progressive_pricing_preset_id: null } : current); setPricingQuote(null); }} /> Preço fixo por foto</label>
                  <label><input type="radio" name="pricing_mode" value="progressive" checked={sales.pricing_mode === "progressive"} onChange={() => setSales((current) => current ? { ...current, pricing_mode: "progressive", fixed_unit_price_cents: null } : current)} /> Preço progressivo por faixas</label>
                </div>
                {sales.pricing_mode === "fixed" ? <label>Valor unitário da foto<input name="fixed_unit_price" inputMode="numeric" value={fixedPriceInput} onChange={(event) => setFixedPriceInput(maskBrazilianCurrencyInput(event.target.value))} placeholder="R$ 7,00" required /></label> : null}
                {sales.pricing_mode === "progressive" ? <div className="gallery-progressive-pricing">
                  <label>Tabela global<select name="progressive_pricing_preset_id" value={sales.progressive_pricing_preset_id ?? ""} onChange={(event) => { setSales((current) => current ? { ...current, progressive_pricing_preset_id: event.target.value || null } : current); setPricingQuote(null); }} required><option value="">Selecione código — nome</option>{pricingPresets.map((preset) => <option key={preset.id} value={preset.id}>{preset.label}</option>)}</select></label>
                  {!pricingPresets.length ? <p className="field-hint">Nenhuma tabela ativa. <Link href="/admin/pricing">Cadastre uma tabela global</Link> antes de salvar.</p> : null}
                  <div className="gallery-pricing-simulator">
                    <label>Quantidade para simular<input type="number" min={1} max={10000} value={quoteQuantity} onChange={(event) => setQuoteQuantity(Number(event.target.value))} /></label>
                    <MarkinaButton type="button" variant="secondary" disabled={!sales.progressive_pricing_preset_id || quoteLoading} onClick={simulatePricing}>{quoteLoading ? "Calculando…" : "Simular valor"}</MarkinaButton>
                  </div>
                  {pricingQuote ? <div className="gallery-pricing-quote" aria-live="polite"><strong>{pricingQuote.quantity} fotos · {formatBrazilianCurrency(pricingQuote.total_cents)}</strong><span>Economia de {formatBrazilianCurrency(pricingQuote.savings_cents)}</span><dl>{pricingQuote.parcels.map((parcel) => <div key={parcel.minimum_quantity}><dt>{parcel.quantity} foto(s) a {formatBrazilianCurrency(parcel.unit_price_cents)}</dt><dd>{formatBrazilianCurrency(parcel.subtotal_cents)}</dd></div>)}</dl></div> : null}
                </div> : null}
                {sales.pricing_review_required || sales.pricing_mode === "legacy_volume" ? <label className="gallery-toggle"><input type="checkbox" checked={confirmLegacyConversion} onChange={(event) => setConfirmLegacyConversion(event.target.checked)} /> Confirmo a substituição das faixas legadas para esta galeria</label> : null}
              </fieldset>
              <fieldset className="gallery-sales-section">
                <legend>PIX manual</legend>
                <label>Chave PIX ou copia e cola<textarea name="pix_copy_paste" rows={3} value={sales.pix.copy_paste ?? ""} onChange={(event) => setSales((current) => current ? { ...current, pix: { ...current.pix, copy_paste: event.target.value || null } } : current)} /></label>
                <p className="field-hint">Aceita CPF, telefone brasileiro, e-mail ou o código completo “PIX copia e cola” gerado pelo banco. Para uma chave simples, os dados abaixo são obrigatórios para montar um QR PIX válido.</p>
                {sales.pix.copy_paste && !sales.pix.copy_paste.trim().startsWith("000201") ? <div className="gallery-pix-receiver-fields">
                  <label>Nome do recebedor<input name="pix_receiver_name" maxLength={25} value={sales.pix.receiver_name ?? ""} onChange={(event) => setSales((current) => current ? { ...current, pix: { ...current.pix, receiver_name: event.target.value || null } } : current)} placeholder="Ex.: MARIA FOTOGRAFIA" /></label>
                  <label>Cidade do recebedor<input name="pix_receiver_city" maxLength={15} value={sales.pix.receiver_city ?? ""} onChange={(event) => setSales((current) => current ? { ...current, pix: { ...current.pix, receiver_city: event.target.value || null } } : current)} placeholder="Ex.: SAO PAULO" /></label>
                </div> : null}
                {sales.pix.review_required ? <p className="notice" role="alert">O PIX anterior diverge do código usado no QR. Corrija o copia-e-cola e salve novamente.</p> : null}
                {sales.pix.qr_png_data_url ? <img className="gallery-pix-qr" src={sales.pix.qr_png_data_url} alt="QR Code PIX gerado a partir da configuração salva" /> : null}
                <label>Instruções de pagamento<textarea name="pix_instructions" rows={3} value={sales.pix.instructions ?? ""} onChange={(event) => setSales((current) => current ? { ...current, pix: { ...current.pix, instructions: event.target.value || null } } : current)} /></label>
              </fieldset>
              <fieldset className="gallery-sales-section">
                <legend>Jornada da cliente</legend>
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
              <p className="gallery-scope-note">Configure como esta galeria será apresentada. A marca-d’água continua global e fica em Configurações.</p>
            </div>
          </div>
          <form id="gallery-details-step" className="gallery-settings-form gallery-visual-settings" onSubmit={saveVisualSettings} onChange={(event) => { setDirty(true); updateVisualPreview(event); }}>
            <div className="gallery-customization-layout">
              <div className="gallery-customization-panels">
                <fieldset className="gallery-customization-panel">
                  <legend>Capa e título</legend>
                  <p>Envie um JPEG dedicado ou escolha uma foto pronta da própria Galeria pública.</p>
                  <input ref={coverUploadInput} type="file" accept="image/jpeg" hidden onChange={uploadCover} />
                  <MarkinaButton type="button" variant="secondary" onClick={() => coverUploadInput.current?.click()}>Enviar imagem de capa</MarkinaButton>
                  {details?.cover_options?.length ? <div className="gallery-cover-options" role="group" aria-label="Opções de capa">{details.cover_options.map((option) => <button type="button" key={option.id} disabled={option.status !== "ready"} aria-pressed={details.settings?.cover_photo_id === option.id} onClick={() => setCoverOption(option)}>{option.preview_url ? <img src={`/api${option.preview_url}`} alt="" /> : <span>Processando</span>}<strong>{option.name}</strong><small>{option.source === "cover_assets" ? "Capa dedicada" : "Foto da galeria"}</small></button>)}</div> : <p className="gallery-scope-note">Nenhuma imagem enviada ainda.</p>}
                  <label>Tipografia do título<select name="cover_title_font" defaultValue={details?.settings?.cover_title_font ?? editor.gallery.cover_title_font}>{details?.font_options?.map((option) => <option key={option.token} value={option.token}>{option.label} · {option.category === "handwritten" ? "Manuscrita" : option.category === "editorial" ? "Editorial" : "Sem serifa"}</option>)}</select></label>
                  <label>Cor do título<input name="cover_title_color" type="color" defaultValue={editor.gallery.cover_title_color} /></label>
                  <label>Tamanho do título<input name="cover_title_size" type="number" min={12} max={96} defaultValue={editor.gallery.cover_title_size} /></label>
                  <label>Posição do título<select name="cover_title_position" defaultValue={editor.gallery.cover_title_position}><option value="top-left">Superior esquerdo</option><option value="top-center">Superior centro</option><option value="top-right">Superior direito</option><option value="middle-left">Centro esquerdo</option><option value="middle-center">Centro</option><option value="middle-right">Centro direito</option><option value="bottom-left">Inferior esquerdo</option><option value="bottom-center">Inferior centro</option><option value="bottom-right">Inferior direito</option></select></label>
                </fieldset>
              </div>
              <aside className="gallery-customization-preview" aria-live="polite">
                <p className="eyebrow">Prévia protegida</p>
                {coverPreviewUrl ? <div className="gallery-customization-preview-image"><img src={`/api${coverPreviewUrl}`} alt="Prévia protegida da capa da galeria" /><strong className={`title-${visualPreview?.cover_title_position ?? "bottom-left"}`} style={{ color: visualPreview?.cover_title_color, fontFamily: titleFontFamily, fontSize: `${Math.min(visualPreview?.cover_title_size ?? 24, 34)}px` }}>{editor.gallery.name}</strong></div> : <div className="gallery-customization-preview-empty"><strong>Envie uma capa para visualizar o título</strong><span>O JPEG será protegido e continuará fora das pastas de conteúdo.</span></div>}
              </aside>
            </div>
          </form>
        </section>
      ) : null}

      {currentStep === "imagens" ? (
        <section className="gallery-editor-panel">
          <div className="section-heading"><div><p className="eyebrow">Etapa 4</p><h2>Imagens e pastas</h2></div><StatusBadge>{folders.length} pasta(s)</StatusBadge></div>
          <p className="gallery-scope-note">Crie pastas, revise os JPEGs e publique somente as fotos prontas. A publicação nunca escolhe clientes privados.</p>
          <fieldset className="gallery-organization-panel">
            <legend>Organização das pastas</legend>
            <label>Exibição das pastas<select aria-label="Exibição das pastas" value={visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode} onChange={saveFolderOrganization}><option value="individual">Pastas lado a lado</option><option value="sequential">Sequência cronológica</option></select></label>
            <div className={`gallery-organization-preview gallery-organization-preview--${visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode}`} aria-label={(visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode) === "sequential" ? "Prévia em sequência cronológica" : "Prévia com pastas lado a lado"}><span>1</span><span>2</span><span>3</span></div>
            <p>{(visualPreview?.folder_display_mode ?? editor.gallery.folder_display_mode) === "sequential" ? "A galeria percorre todas as pastas em sequência cronológica." : "A cliente escolhe uma pasta por vez para navegar."}</p>
          </fieldset>
          <form className="gallery-inline-form" onSubmit={createFolder}><label>Nome da nova pasta<input name="name" required placeholder="Ex.: Apresentação da manhã" /></label><MarkinaButton disabled={!editor.actions.can_create_folder}>Criar pasta</MarkinaButton></form>
          {folders.length ? <div className="gallery-folder-grid">{folders.map((folder) => <article key={folder.id} className={`${folderPublicationClass(folder)} ${folder.id === openFolderId ? "is-open" : ""}`}><button type="button" onClick={() => inspectFolder(folder.id)}><span className="gallery-folder-cover">{folder.preview_url ? <img src={`/api${folder.preview_url}`} alt="" /> : null}<b>{folder.photo_count ? `${folder.photo_count} fotos` : "Pasta vazia"}</b></span><strong>{folder.name}</strong><small>{folder.status === "released" ? "Publicada" : "Em preparação"}</small><FolderPublicationSummary folder={folder} /></button>{folder.status === "preparing" ? <div className="gallery-folder-actions"><button type="button" className="link-button" onClick={() => { const name = window.prompt("Novo nome da pasta", folder.name); if (name) mutate(`/api/admin/photo-folders/${folder.id}`, "PATCH", { name }); }}>Renomear</button>{folder.photo_count === 0 ? <button type="button" className="link-button" onClick={() => { if (window.confirm("Excluir esta pasta vazia?")) mutate(`/api/admin/photo-folders/${folder.id}`, "DELETE"); }}>Excluir</button> : null}</div> : null}</article>)}</div> : <SystemState title="Nenhuma pasta nesta galeria" detail="Crie a primeira pasta para iniciar o carregamento das fotos." />}
          {selectedFolder ? (
            <div className="gallery-folder-workspace">
              <div className="section-heading"><div><p className="eyebrow">Pasta selecionada</p><h3>{selectedFolder.name}</h3></div><StatusBadge tone={selectedFolder.status === "released" ? "success" : "warning"}>{selectedFolder.status === "released" ? "Publicada" : "Em preparação"}</StatusBadge></div>
              {uploadState.phase !== "idle" ? <div className={`upload-status upload-status--${uploadState.phase}`} role="status"><strong>{uploadState.phase === "uploading" ? `Enviando foto ${uploadState.current} de ${uploadState.total}` : uploadState.phase === "success" ? "Upload concluído" : "Falha no upload"}</strong>{uploadState.filename ? <span>{uploadState.filename}</span> : null}{uploadState.phase === "uploading" ? <progress value={uploadState.current} max={uploadState.total} /> : null}</div> : null}
              {photos.length ? <><div className="folder-photo-toolbar"><label><input type="checkbox" checked={photos.length > 0 && selectedPhotoIds.length === photos.length} onChange={(event) => setSelectedPhotoIds(event.target.checked ? photos.map((photo) => photo.id) : [])} /> Selecionar todas</label><MarkinaButton type="button" className="mk-button--danger" disabled={!selectedPhotoIds.some((id) => photos.some((photo) => photo.id === id && photo.can_delete))} onClick={deleteSelectedPhotos}>Excluir selecionadas</MarkinaButton></div><div className="folder-photo-grid">{photos.map((photo) => <article key={photo.id} className={`photo-state-${photo.publication_state ?? "processing"}`}><label className="photo-select"><input type="checkbox" checked={selectedPhotoIds.includes(photo.id)} disabled={!photo.can_delete} onChange={(event) => setSelectedPhotoIds((current) => event.target.checked ? [...current, photo.id] : current.filter((id) => id !== photo.id))} /> {photo.can_delete ? "Selecionar" : "Compra confirmada"}</label>{photo.preview_url ? <button type="button" className="photo-preview-button" onClick={() => setExpandedPhoto(photo)} aria-label={`Ampliar ${photo.name}`}><img src={`/api${photo.preview_url}`} alt={`Prévia com marca d’água de ${photo.name}`} /></button> : <div className="gallery-cover">Processando</div>}<strong>{photo.name}</strong><small>{photo.error ?? (photo.publication_state === "published" ? "Publicada" : photo.publication_state === "ready_to_publish" ? "Pronta para publicar" : photo.publication_state === "failed" ? "Falha no processamento" : "Processando")}</small><div className="photo-card-actions"><button type="button" className="link-button" disabled={!photo.preview_url || photo.is_cover} onClick={() => setCover(photo)}>{photo.is_cover ? "Capa atual" : "Usar como capa"}</button><button type="button" className="link-button danger-action" disabled={!photo.can_delete} title={photo.can_delete ? "Excluir foto" : "Há uma compra confirmada para esta foto"} onClick={() => deletePhoto(photo)}>{photo.can_delete ? "Excluir" : "Compra confirmada"}</button></div></article>)}</div></> : <SystemState title="Pasta sem fotos" detail="Selecione os JPEGs abaixo para iniciar o processamento." />}
              <form ref={uploadForm} className="gallery-inline-form" onSubmit={uploadPhotos}><input name="folder" type="hidden" value={selectedFolder.id} /><input ref={uploadInput} name="jpeg" type="file" accept="image/jpeg" multiple required hidden onChange={() => uploadForm.current?.requestSubmit()} /><MarkinaButton type="button" disabled={!editor.actions.can_upload} onClick={() => uploadInput.current?.click()}>Carregar fotos</MarkinaButton><MarkinaButton type="button" disabled={!photos.some((photo) => photo.publication_state === "ready_to_publish" || (!photo.publication_state && photo.preview_url))} onClick={() => publishFolder(selectedFolder.id)}>{selectedFolder.status === "released" ? "Publicar novas fotos prontas" : "Publicar pasta na Galeria pública"}</MarkinaButton></form>
            </div>
          ) : null}
        </section>
      ) : null}

      {currentStep === "clientes" ? (
        <section className="gallery-editor-panel">
          <div className="section-heading"><div><p className="eyebrow">Etapa 5</p><h2>Clientes e acesso</h2></div><StatusBadge>{linkedClients.length} vínculo(s)</StatusBadge></div>
          <div className="unlisted-link"><span>Link fixo da Galeria pública</span><strong>{publicLink?.status === "active" ? "Ativo" : publicLink?.status === "legacy_unrecoverable" ? "Link antigo precisa ser regenerado" : "Ainda não disponível"}</strong>{publicLink?.link ? <input aria-label="Link da Galeria pública" readOnly value={publicLink.link} onFocus={(event) => event.currentTarget.select()} /> : null}<small>A cliente ainda precisará concluir o login contextual por nome, telefone e código. Regenerar revoga imediatamente o endereço anterior.</small><div className="gallery-access-actions">{publicLink?.link ? <MarkinaButton type="button" variant="secondary" onClick={() => copyAccessLink(publicLink.link, "Link público")}>Copiar link</MarkinaButton> : null}<MarkinaButton type="button" disabled={Boolean(accessBusy)} onClick={() => changePublicLink(publicLink?.status === "active" ? "rotate" : "create")}>{publicLink?.status === "active" ? "Regenerar link" : "Criar link"}</MarkinaButton></div></div>
          <div className="gallery-client-grid">
            <section className="gallery-client-card" aria-labelledby="linked-clients-title">
              <p className="eyebrow">Acesso atual</p>
              <h3 id="linked-clients-title">Clientes vinculadas</h3>
              <p className="gallery-scope-note">Pessoas que já possuem cadastro ou galeria privada associada a este evento.</p>
              {unlinkTarget && (unlinkOperation || (unlinkError && !unlinkPreview)) ? <section className={`unlink-progress${unlinkError || unlinkOperation?.status === "failed" ? " unlink-progress--error" : ""}`} aria-label={`Desvinculação de ${unlinkTarget.name}`} aria-live="polite"><div><strong>{unlinkOperation?.progress.label ?? "Não foi possível desvincular"}</strong>{unlinkOperation ? <span>{unlinkOperation.progress.percent}%</span> : null}</div>{unlinkOperation ? <progress value={unlinkOperation.progress.percent} max={100} /> : null}<p>{unlinkError || unlinkOperation?.last_error || (unlinkOperation?.status === "completed" ? "Cliente desvinculada. Cadastro e histórico foram preservados." : unlinkOperation?.status === "cancelled" ? "Desvinculação cancelada antes da remoção física." : "A desvinculação continua em segundo plano.")}</p><div>{unlinkOperation?.actions.can_cancel ? <MarkinaButton type="button" variant="secondary" disabled={unlinkBusy} onClick={() => unlinkOperationAction("cancel")}>Cancelar desvinculação</MarkinaButton> : null}{unlinkOperation?.actions.can_retry ? <MarkinaButton type="button" disabled={unlinkBusy} onClick={() => unlinkOperationAction("retry")}>Retomar desvinculação</MarkinaButton> : null}{!unlinkOperation?.actions.should_poll ? <MarkinaButton type="button" variant="secondary" onClick={() => { setUnlinkOperation(null); setUnlinkTarget(null); setUnlinkError(""); }}>Fechar</MarkinaButton> : null}</div></section> : null}
              {linkedClients.length ? (
                <div className="gallery-linked-clients" aria-label="Lista de clientes vinculadas">
                  {linkedClients.map((person) => <ClientGalleryCard key={person.client_id} person={person} actions={<><MarkinaButton type="button" variant="secondary" onClick={() => { setPrivateTarget(person); setAdminPhotoIds([]); setPrivateActionError(""); }}>Montar galeria privada</MarkinaButton><MarkinaButton type="button" variant="secondary" className="gallery-client-unlink" disabled={unlinkBusy || Boolean(unlinkOperation?.actions.should_poll)} onClick={() => openUnlinkConfirmation(person)}>Desvincular cliente</MarkinaButton></>} />)}
                </div>
              ) : <SystemState title="Nenhuma cliente vinculada" detail="Use a busca ou o novo cadastro para criar o primeiro vínculo." />}
            </section>
            <section className="gallery-client-card" aria-labelledby="existing-client-title">
              <p className="eyebrow">Cadastro existente</p>
              <h3 id="existing-client-title">Vincular cliente</h3>
              <label className="gallery-client-search">Buscar por nome ou WhatsApp<input value={clientQuery} onChange={(event) => setClientQuery(event.target.value)} placeholder="Ex.: Ana ou 11999999999" /></label>
              {clientOptions.length ? <div className="client-option-list">{clientOptions.map((option) => {
                const linked = linkedClients.some((person) => person.client_id === option.id);
                return <div className="client-option-row" key={option.id}><span><strong>{option.name}</strong><small>{option.phone}</small></span><div className="client-option-actions">{linked ? <StatusBadge tone="success">Já vinculada</StatusBadge> : <button type="button" className="client-option-action" aria-label={`Vincular ${option.name}`} onClick={() => bindClient(option.id, option.name)}>Vincular</button>}<button type="button" className="client-option-edit" aria-label={`Editar cadastro de ${option.name}`} onClick={() => openClientEditor(option)}>Editar</button></div></div>;
              })}</div> : <SystemState title="Nenhum cadastro encontrado" detail="Revise a busca ou use o bloco Novo cadastro." />}
            </section>
            <section className="gallery-client-card" aria-labelledby="new-client-title">
              <p className="eyebrow">Novo cadastro</p>
              <h3 id="new-client-title">Cadastrar e vincular</h3>
              <p className="gallery-scope-note">Crie o cadastro somente quando a cliente ainda não aparecer na busca.</p>
              <form className="gallery-settings-form" onSubmit={createClientAndGallery}><label>Nome completo<input name="full_name" required minLength={3} /></label><label>Número do WhatsApp<input name="phone_e164" required placeholder="+55 11 99999-9999" /></label><MarkinaButton>Cadastrar cliente</MarkinaButton></form>
            </section>
          </div>
          <section className="private-access-manager" aria-labelledby="private-access-title">
            <div className="section-heading"><div><p className="eyebrow">Acesso compartilhado</p><h3 id="private-access-title">Galerias privadas e membros</h3><p className="gallery-scope-note">Cada galeria tem um acervo comum, mas seleção, favoritos, pedidos e pagamentos permanecem individuais.</p></div></div>
            {!Object.keys(privateAccess).length ? <SystemState title="Nenhuma galeria privada criada" detail="Use Montar galeria privada em uma cliente para escolher as fotos do primeiro acervo privado." /> : <div className="private-access-list">{Object.entries(privateAccess).map(([galleryId, access]) => {
              const galleryOwner = linkedClients.find((client) => client.derived_gallery_id === galleryId);
              const availableCandidates = clientOptions.filter((client) => !access.members.some((member) => member.client_id === client.id));
              return <article className="private-access-card" key={galleryId} aria-label={`Galeria privada ${galleryOwner?.name ?? galleryId}`}>
                <header><div><strong>{galleryOwner?.name ? `Galeria de ${galleryOwner.name}` : "Galeria privada"}</strong><small>ID {galleryId}</small></div><StatusBadge tone={access.link?.status === "active" ? "success" : "warning"}>{access.link?.status === "active" ? "Link ativo" : "Sem link atual"}</StatusBadge></header>
                {access.loading ? <SystemState tone="loading" title="Carregando acesso" detail="Consultando link e membros." /> : access.error ? <SystemState tone="error" title="Acesso indisponível" detail={access.error} /> : <>
                  <div className="private-link-row">{access.link?.link ? <input aria-label={`Link privado de ${galleryOwner?.name ?? galleryId}`} readOnly value={access.link.link} onFocus={(event) => event.currentTarget.select()} /> : <span>{access.link?.status === "legacy_unrecoverable" ? "O link antigo não pode ser reconstruído." : "Crie o link compartilhável desta galeria."}</span>}<div className="gallery-access-actions">{access.link?.link ? <MarkinaButton type="button" variant="secondary" onClick={() => copyAccessLink(access.link?.link ?? null, "Link privado")}>Copiar</MarkinaButton> : null}<MarkinaButton type="button" disabled={Boolean(accessBusy)} onClick={() => changePrivateLink(galleryId, access.link?.status === "active" ? "rotate" : access.link?.status === "legacy_unrecoverable" ? "rotate" : "create")}>{access.link?.status === "active" ? "Regenerar" : "Criar link"}</MarkinaButton></div></div>
                  <div className="private-member-list">{access.members.length ? access.members.map((member) => <div className={`private-member-row private-member-row--${member.status}`} key={member.membership_id}><div><strong>{member.client_name}</strong><small>{member.phone_e164 ?? "Telefone indisponível"}</small></div><StatusBadge tone={member.status === "active" ? "success" : member.status === "blocked" ? "dark" : "neutral"}>{member.status === "active" ? "Ativa" : member.status === "blocked" ? "Bloqueada" : "Desvinculada"}</StatusBadge><dl><div><dt>Selecionadas</dt><dd>{member.selected_count}</dd></div><div><dt>Compradas</dt><dd>{member.purchased_count}</dd></div><div><dt>Pedidos</dt><dd>{member.order_count}</dd></div></dl><div className="gallery-access-actions">{member.status === "active" ? <MarkinaButton type="button" variant="secondary" disabled={Boolean(accessBusy)} onClick={() => changePrivateMember(galleryId, member, "block")}>Bloquear</MarkinaButton> : member.status === "blocked" ? <MarkinaButton type="button" variant="secondary" disabled={Boolean(accessBusy)} onClick={() => changePrivateMember(galleryId, member, "unblock")}>Desbloquear</MarkinaButton> : null}{member.status !== "unlinked" ? <MarkinaButton type="button" variant="quiet" disabled={Boolean(accessBusy)} onClick={() => changePrivateMember(galleryId, member, "unlink")}>Desvincular</MarkinaButton> : null}</div></div>) : <SystemState title="Nenhum membro" detail="Adicione uma cliente cadastrada abaixo." />}</div>
                  <div className="private-member-add"><label>Adicionar cliente a esta privada<select aria-label={`Adicionar cliente à galeria de ${galleryOwner?.name ?? galleryId}`} value={memberCandidateByGallery[galleryId] ?? ""} onChange={(event) => setMemberCandidateByGallery((current) => ({ ...current, [galleryId]: event.target.value }))}><option value="">Selecione uma cliente</option>{availableCandidates.map((client) => <option key={client.id} value={client.id}>{client.name} · {client.phone}</option>)}</select></label><MarkinaButton type="button" disabled={!memberCandidateByGallery[galleryId] || Boolean(accessBusy)} onClick={() => addPrivateMember(galleryId)}>Adicionar membro</MarkinaButton></div>
                </>}
              </article>;
            })}</div>}
          </section>
        </section>
      ) : null}

      {expandedPhoto ? <div className="photo-preview-dialog" role="presentation" onMouseDown={() => setExpandedPhoto(null)}><div ref={previewDialog} role="dialog" aria-modal="true" aria-label={`Prévia ampliada de ${expandedPhoto.name}`} tabIndex={-1} onKeyDown={(event) => { if (event.key === "Escape") setExpandedPhoto(null); }} onMouseDown={(event) => event.stopPropagation()}><button type="button" className="photo-preview-close" onClick={() => setExpandedPhoto(null)}>Fechar</button><img src={`/api${expandedPhoto.preview_url}`} alt={`Prévia com marca d’água ampliada de ${expandedPhoto.name}`} /><p>{expandedPhoto.name}</p></div></div> : null}
      {clientEditTarget ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="edit-client-title" aria-modal="true" className="mk-dialog client-edit-dialog" role="dialog"><p className="eyebrow">Cadastro da cliente</p><h2 id="edit-client-title">Editar {clientEditTarget.name}</h2><p>Atualize a mesma identidade para preservar galerias e histórico. A troca de WhatsApp exige o código enviado ao novo número.</p><form className="gallery-settings-form" onSubmit={saveClient}><label>Nome completo<input value={clientEditName} required minLength={3} onChange={(event) => setClientEditName(event.target.value)} /></label><label>Número do WhatsApp<input value={clientEditPhone} required placeholder="+55 11 99999-9999" onChange={(event) => { setClientEditPhone(event.target.value); setClientEditChallengeId(""); setClientEditOtp(""); }} /></label>{clientEditChallengeId ? <label>Código enviado ao novo WhatsApp<input value={clientEditOtp} inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} required onChange={(event) => setClientEditOtp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label> : null}{clientEditError ? <p className="form-message form-message--error" role="alert">{clientEditError}</p> : null}<div className="mk-dialog__actions"><MarkinaButton type="button" variant="secondary" disabled={clientEditBusy} onClick={closeClientEditor}>Cancelar</MarkinaButton><MarkinaButton disabled={clientEditBusy}>{clientEditBusy ? "Salvando…" : clientEditPhone.trim() !== clientEditTarget.phone && !clientEditChallengeId ? "Enviar código" : "Salvar cadastro"}</MarkinaButton></div></form><div className="client-delete-zone"><strong>Excluir cadastro criado por engano</strong><p>Troca de telefone deve ser feita acima. A exclusão só é permitida sem vínculos ou histórico.</p>{!clientDeletionInventory ? <MarkinaButton type="button" variant="quiet" disabled={clientEditBusy} onClick={inspectClientDeletion}>Verificar exclusão</MarkinaButton> : clientDeletionInventory.can_delete ? <><p>Este cadastro não possui dependências protegidas.</p><MarkinaButton type="button" className="mk-button--danger" disabled={clientEditBusy} onClick={confirmClientDeletion}>Excluir cadastro definitivamente</MarkinaButton></> : <div className="client-delete-blocked" role="status"><strong>Exclusão bloqueada</strong><ul>{Object.entries(clientDeletionInventory.blocking).map(([key, quantity]) => <li key={key}>{quantity} {clientBlockerLabels[key] ?? key}</li>)}</ul><p>Use a edição do telefone ou desvincule a cliente da galeria.</p></div>}</div></section></div> : null}
      {unlinkPreview ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="unlink-client-title" aria-modal="true" className="mk-dialog" role="dialog"><p className="eyebrow">Desvinculação da Galeria pública</p><h2 id="unlink-client-title">Desvincular {unlinkPreview.target.client_name}?</h2><p>O acesso desta cliente será encerrado nesta Galeria pública e na privada associada. O cadastro, as outras galerias e todo histórico comercial serão preservados; o acervo privado compartilhado permanece para os demais membros.</p><div className="unlink-summary"><span><strong>{unlinkPreview.inventory.remove.memberships ?? 0}</strong> vínculo privado</span><span><strong>{unlinkPreview.inventory.remove.selections ?? 0}</strong> selecionadas removíveis</span><span><strong>{typeof unlinkPreview.inventory.preserve.orders === "number" ? unlinkPreview.inventory.preserve.orders : 0}</strong> pedidos preservados</span><span><strong>{typeof unlinkPreview.inventory.preserve.available_references === "number" ? unlinkPreview.inventory.preserve.available_references : 0}</strong> fotos preservadas</span></div><p>Um pagamento informado e ainda em análise impede a desvinculação até a decisão administrativa.</p>{unlinkError ? <p className="form-message form-message--error" role="alert">{unlinkError}</p> : null}<div className="mk-dialog__actions"><MarkinaButton type="button" variant="secondary" disabled={unlinkBusy} onClick={() => { setUnlinkPreview(null); setUnlinkTarget(null); setUnlinkError(""); }}>Cancelar</MarkinaButton><MarkinaButton type="button" className="mk-button--danger" disabled={unlinkBusy} onClick={confirmUnlink}>{unlinkBusy ? "Iniciando…" : "Confirmar desvinculação"}</MarkinaButton></div></section></div> : null}
      {privateTarget ? <div className="mk-dialog-backdrop" role="presentation"><section aria-labelledby="private-gallery-title" aria-modal="true" className="mk-dialog administrative-private-dialog" role="dialog"><p className="eyebrow">Montagem administrativa</p><h2 id="private-gallery-title">Galeria privada de {privateTarget.name}</h2>{availablePhotos.length ? <><p>Escolha fotos já publicadas para compor o acervo privado. Esta ação não favorita, não seleciona e não cria pedido em nome da cliente.</p><form onSubmit={createAdministrativePrivateGallery}><fieldset><legend>Fotos disponíveis</legend><div className="administrative-photo-options">{availablePhotos.map((photo) => <label key={photo.id}><input type="checkbox" checked={adminPhotoIds.includes(photo.id)} onChange={(event) => setAdminPhotoIds((current) => event.target.checked ? [...current, photo.id] : current.filter((id) => id !== photo.id))} /><span><strong>{photo.name}</strong><small>{photo.folder_name}</small></span></label>)}</div></fieldset>{privateActionError ? <p className="form-message form-message--error" role="alert">{privateActionError}</p> : null}<div className="mk-dialog__actions"><MarkinaButton type="button" variant="secondary" disabled={privateActionBusy} onClick={() => { setPrivateTarget(null); setAdminPhotoIds([]); setPrivateActionError(""); }}>Cancelar</MarkinaButton><MarkinaButton disabled={!adminPhotoIds.length || privateActionBusy}>{privateActionBusy ? "Salvando…" : "Criar ou atualizar galeria privada"}</MarkinaButton></div></form></> : <><SystemState title="Nenhuma foto publicada" detail="Use Salvar e avançar na etapa Imagens depois que o processamento terminar. As fotos publicadas poderão então compor esta privada." /><div className="mk-dialog__actions"><MarkinaButton type="button" variant="secondary" onClick={() => { setPrivateTarget(null); setPrivateActionError(""); }}>Fechar</MarkinaButton><Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}/edit/imagens`}>Ir para Imagens</Link></div></>}</section></div> : null}
      {message ? <p className="notice" role="status">{message}</p> : null}
      <footer className="gallery-editor-footer">
        {previous ? <Link className="mk-button mk-button--secondary" href={`/admin/galleries/sources/${sourceId}/edit/${previous}`} onClick={confirmDiscard}>← Voltar</Link> : <span />}
        {next && activeEditableForm ? <MarkinaButton type="submit" form={activeEditableForm} disabled={savingStep}>{savingStep ? "Salvando…" : "Salvar e avançar →"}</MarkinaButton> : currentStep === "imagens" ? <MarkinaButton type="button" disabled={savingStep} onClick={publishReadyAndAdvance}>{savingStep ? "Publicando…" : "Salvar e avançar →"}</MarkinaButton> : next ? <Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}/edit/${next}`}>Avançar →</Link> : <Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${sourceId}`}>Concluir</Link>}
      </footer>
    </main>
  );
}
