"use client";

import { FormEvent, KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";

import { MarkinaButton, MetricCard, StatusBadge, SurfaceCard, SystemState } from "../../ui-kit";
import CreditHistory, { type HistoryPage } from "./credit-history";
import styles from "./owner-credit-operations.module.css";
import { OwnerMediaArchiveRecoveries, type OwnerRecovery } from "./owner-media-archive-recoveries";

type Wallet = {
  mode: "finite" | "unmetered";
  available_credits: number | null;
  reserved_credits: number;
  pending_operations: number;
  pending_upload_operations?: number;
  pending_recovery_operations?: number;
  recent_consumed_credits: number;
  recent_period_days: number;
  can_upload_content: boolean | null;
  state?: "available" | "unavailable";
};

type TenantSuggestion = {
  tenant_id: string;
  status: string;
  canonical_host: string | null;
  photographer_name: string | null;
  admin_email: string | null;
};

type TenantView = "" | "all" | "alphabetical" | "recent";
type TenantPage = { items: TenantSuggestion[]; has_more?: boolean };

function tenantSearchParameters(query: string, mode: TenantView, offset = 0): URLSearchParams {
  const parameters = new URLSearchParams({ query: query.trim(), limit: "10", offset: String(offset) });
  if (mode) parameters.set("mode", mode);
  return parameters;
}

type CreditEntry = {
  id: string;
  type: string;
  delta: number;
  source_reference: string | null;
  description: string | null;
  created_at: string;
};

type RevocableGrant = CreditEntry & {
  quantity: number;
  revocable_quantity: number;
};

type TenantDetail = {
  wallet: Wallet;
  entries: CreditEntry[];
  history?: HistoryPage;
  revocable_grants: RevocableGrant[];
  financial_reviews: FinancialReview[];
  media_archive_recoveries?: OwnerRecovery[];
};

type FinancialReviewEvent = {
  event_type: string;
  occurred_at: string;
  details: Record<string, unknown>;
};

type FinancialReview = {
  purchase_id: string;
  tenant_id: string;
  photographer_email: string | null;
  package_name: string;
  credit_quantity: number;
  total_cents: number;
  currency_code: string;
  payment_state: string;
  review_status: "pending" | "released" | "restricted" | "none";
  review_note: string | null;
  reviewed_by_admin_id: string | null;
  created_at: string;
  reviewed_at: string | null;
  events: FinancialReviewEvent[];
};

type JsonRecord = Record<string, unknown>;

async function readJson<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    throw new Error(typeof payload?.detail === "string" ? payload.detail : "Não foi possível concluir a operação.");
  }
  return payload as T;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

function formatPackagePrice(priceCents: number, currencyCode: string): string {
  try {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: currencyCode })
      .format(priceCents / 100);
  } catch {
    return `${priceCents} centavos · ${currencyCode}`;
  }
}

function reviewStateLabel(state: string): string {
  return {
    refunded: "Reembolso total",
    partially_refunded: "Reembolso parcial",
    charged_back: "Chargeback",
  }[state] ?? "Ocorrência financeira";
}

function tenantLabel(item: TenantSuggestion): string {
  const identity = item.photographer_name || item.admin_email || "Identidade indisponível";
  const email = item.photographer_name && item.admin_email ? ` · ${item.admin_email}` : "";
  const host = item.canonical_host ? ` · ${item.canonical_host}` : "";
  return `${identity}${email}${host} · ${item.tenant_id.slice(0, 8)}`;
}

export function OwnerCreditOperations() {
  const [tenants, setTenants] = useState<TenantSuggestion[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [tenantView, setTenantView] = useState<TenantView>("");
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [hasMoreTenants, setHasMoreTenants] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState("");
  const moreController = useRef<AbortController | null>(null);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const [listState, setListState] = useState<"idle" | "loading" | "ready" | "failed">("idle");
  const searchSequence = useRef(0);
  const [selectedTenantId, setSelectedTenantId] = useState("");
  const [selectedTenant, setSelectedTenant] = useState<TenantSuggestion | null>(null);
  const [loadedDetail, setLoadedDetail] = useState<TenantDetail | null>(null);
  const [detailTenantId, setDetailTenantId] = useState("");
  const [detailRefreshVersion, setDetailRefreshVersion] = useState(-1);
  const [detailState, setDetailState] = useState<"ready" | "failed">("ready");
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [grantQuantity, setGrantQuantity] = useState("");
  const [grantReference, setGrantReference] = useState("");
  const [grantPassword, setGrantPassword] = useState("");
  const [grantTotp, setGrantTotp] = useState("");
  const [revokeGrantId, setRevokeGrantId] = useState("");
  const [revokeQuantity, setRevokeQuantity] = useState("");
  const [revokeReference, setRevokeReference] = useState("");
  const [revokePassword, setRevokePassword] = useState("");
  const [revokeTotp, setRevokeTotp] = useState("");
  const [saving, setSaving] = useState<"grant" | "revoke" | null>(null);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const idempotencyKeys = useRef(new Map<string, string>());
  const requestIds = useRef(new Map<string, string>());
  const [reviewQueue, setReviewQueue] = useState<FinancialReview[]>([]);
  const [reviewQueueState, setReviewQueueState] = useState<"loading" | "ready" | "failed">("loading");
  const [reviewQueueError, setReviewQueueError] = useState("");
  const [reviewReasons, setReviewReasons] = useState<Record<string, string>>({});
  const [reviewingPurchaseId, setReviewingPurchaseId] = useState<string | null>(null);
  const [reviewPassword, setReviewPassword] = useState("");
  const [reviewTotp, setReviewTotp] = useState("");
  const [reviewActionError, setReviewActionError] = useState("");
  const [reviewActionMessage, setReviewActionMessage] = useState("");
  const reviewRequestIds = useRef(new Map<string, string>());
  const financialMutationInFlight = saving !== null || reviewingPurchaseId !== null;

  const loadReviewQueue = useCallback(async (signal?: AbortSignal) => {
    setReviewQueueState("loading");
    try {
      const response = await fetch("/api/admin/platform/credit-purchases/reviews", {
        credentials: "same-origin",
        cache: "no-store",
        signal,
      });
      const result = await readJson<{ items: FinancialReview[] }>(response);
      setReviewQueue(result.items);
      setReviewQueueState("ready");
      setReviewQueueError("");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setReviewQueueError(error instanceof Error ? error.message : "Não foi possível carregar a fila de revisão.");
      setReviewQueueState("failed");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // A resposta assíncrona hidrata a fila; não há atualização antes da rede.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadReviewQueue(controller.signal);
    return () => controller.abort();
  }, [loadReviewQueue]);

  useEffect(() => {
    const query = searchQuery.trim();
    if (!suggestionsOpen || (!tenantView && query.length < 2)) return;
    const sequence = ++searchSequence.current;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const parameters = tenantSearchParameters(query, tenantView);
      setListState("loading");
      fetch(`/api/admin/platform/credit-tenants/search?${parameters.toString()}`, {
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal,
      })
        .then((response) => readJson<TenantPage>(response))
        .then((result) => {
          if (controller.signal.aborted || searchSequence.current !== sequence) return;
          setTenants(result.items);
          setHasMoreTenants(Boolean(result.has_more));
          setActiveSuggestion(-1);
          setListState("ready");
        })
        .catch((error: unknown) => {
          if ((error instanceof DOMException && error.name === "AbortError")
            || controller.signal.aborted || searchSequence.current !== sequence) return;
          setListState("failed");
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
      moreController.current?.abort();
    };
  }, [searchQuery, tenantView, suggestionsOpen]);

  useEffect(() => {
    if (!selectedTenantId) return;
    const controller = new AbortController();
    fetch(`/api/admin/platform/credit-tenants/${selectedTenantId}`, {
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
    })
      .then((response) => readJson<TenantDetail>(response))
      .then((result) => {
        setLoadedDetail(result);
        setDetailTenantId(selectedTenantId);
        setDetailRefreshVersion(refreshVersion);
        setDetailState("ready");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setDetailTenantId(selectedTenantId);
        setDetailRefreshVersion(refreshVersion);
        setDetailState("failed");
      });
    return () => controller.abort();
  }, [selectedTenantId, refreshVersion]);

  const detailIsCurrent = Boolean(
    selectedTenantId && detailTenantId === selectedTenantId && detailRefreshVersion === refreshVersion,
  );
  const detail = detailIsCurrent ? loadedDetail : null;
  const currentDetailState = !selectedTenantId ? "empty" : !detailIsCurrent ? "loading" : detailState;
  const activeGrantSources = detail?.revocable_grants.filter((grant) => grant.revocable_quantity > 0) ?? [];
  const operationsAvailable = Boolean(
    selectedTenant && detail?.wallet.mode === "finite" && detail.wallet.state !== "unavailable",
  );

  function selectTenant(item: TenantSuggestion) {
    if (financialMutationInFlight) return;
    closeSuggestions();
    setSelectedTenant(item);
    setSelectedTenantId(item.tenant_id);
    setSearchQuery("");
    clearTenantOperationForm();
    setActionError("");
    setActionMessage("");
  }

  function clearTenantOperationForm() {
    setGrantQuantity("");
    setGrantReference("");
    setGrantPassword("");
    setGrantTotp("");
    setRevokeGrantId("");
    setRevokeQuantity("");
    setRevokeReference("");
    setRevokePassword("");
    setRevokeTotp("");
  }

  function closeSuggestions() {
    searchSequence.current += 1;
    moreController.current?.abort();
    moreController.current = null;
    setSuggestionsOpen(false);
    setTenants([]);
    setHasMoreTenants(false);
    setLoadingMore(false);
    setMoreError("");
    setActiveSuggestion(-1);
    setListState("idle");
  }

  function changeTenantSearch(query: string, mode: TenantView) {
    if (financialMutationInFlight) return;
    closeSuggestions();
    setSearchQuery(query);
    setTenantView(mode);
    setSelectedTenant(null);
    setSelectedTenantId("");
    setLoadedDetail(null);
    clearTenantOperationForm();
    setActionError("");
    setActionMessage("");
    const shouldSearch = Boolean(mode) || query.trim().length >= 2;
    setSuggestionsOpen(shouldSearch);
    setListState(shouldSearch ? "loading" : "idle");
  }

  async function loadMoreTenants() {
    if (financialMutationInFlight || !suggestionsOpen || !hasMoreTenants || moreController.current) return;
    const sequence = searchSequence.current;
    const controller = new AbortController();
    moreController.current = controller;
    setLoadingMore(true);
    setMoreError("");
    try {
      const parameters = tenantSearchParameters(searchQuery, tenantView, tenants.length);
      const response = await fetch(`/api/admin/platform/credit-tenants/search?${parameters}`, {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
      });
      const result = await readJson<TenantPage>(response);
      if (controller.signal.aborted || searchSequence.current !== sequence) return;
      setTenants((current) => {
        const known = new Set(current.map((item) => item.tenant_id));
        return [...current, ...result.items.filter((item) => {
          if (known.has(item.tenant_id)) return false;
          known.add(item.tenant_id);
          return true;
        })];
      });
      setHasMoreTenants(Boolean(result.has_more));
    } catch (error) {
      if (controller.signal.aborted || searchSequence.current !== sequence) return;
      setMoreError(error instanceof Error ? error.message : "Não foi possível carregar mais fotógrafos.");
    } finally {
      if (moreController.current === controller) moreController.current = null;
      if (searchSequence.current === sequence) setLoadingMore(false);
    }
  }

  function handleSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (financialMutationInFlight) return;
    if (event.key === "ArrowDown" && tenants.length) {
      event.preventDefault();
      setActiveSuggestion((current) => Math.min(current + 1, tenants.length - 1));
    } else if (event.key === "ArrowUp" && tenants.length) {
      event.preventDefault();
      setActiveSuggestion((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && activeSuggestion >= 0 && tenants[activeSuggestion]) {
      event.preventDefault();
      selectTenant(tenants[activeSuggestion]);
    } else if (event.key === "Escape") {
      closeSuggestions();
      setSearchQuery("");
    }
  }

  function idempotencyKey(signature: string): string {
    const existing = idempotencyKeys.current.get(signature);
    if (existing) return existing;
    const generated = `owner-credit-${crypto.randomUUID()}`;
    idempotencyKeys.current.set(signature, generated);
    return generated;
  }

  function requestId(signature: string): string {
    const existing = requestIds.current.get(signature);
    if (existing) return existing;
    const generated = crypto.randomUUID();
    requestIds.current.set(signature, generated);
    return generated;
  }

  async function grantCredits(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTenant || !operationsAvailable || financialMutationInFlight) return;
    const quantity = Number(grantQuantity);
    const reference = grantReference.trim();
    if (!Number.isSafeInteger(quantity) || quantity < 1 || !reference || !grantPassword || !/^\d{6}$/.test(grantTotp)) {
      setActionError("Informe a quantidade, a referência, sua senha atual e o código de 6 dígitos do autenticador.");
      return;
    }
    const signature = JSON.stringify(["grant", selectedTenant.tenant_id, quantity, reference]);
    setSaving("grant");
    setActionError("");
    setActionMessage("");
    try {
      const response = await fetch("/api/admin/platform/credit-grants", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId(signature),
          tenant_id: selectedTenant.tenant_id,
          quantity,
          reference,
          idempotency_key: idempotencyKey(signature),
          current_password: grantPassword,
          totp_code: grantTotp,
        }),
      });
      await readJson<{ entry: CreditEntry; wallet: Wallet }>(response);
      idempotencyKeys.current.delete(signature);
      requestIds.current.delete(signature);
      setGrantQuantity("");
      setGrantReference("");
      setGrantPassword("");
      setGrantTotp("");
      setActionMessage("Concessão registrada e auditada.");
      setRefreshVersion((value) => value + 1);
    } catch (error) {
      setGrantTotp("");
      setActionError(error instanceof Error ? error.message : "Não foi possível conceder créditos.");
    } finally {
      setSaving(null);
    }
  }

  async function revokeCredits(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTenant || !operationsAvailable || financialMutationInFlight) return;
    const source = activeGrantSources.find((grant) => grant.id === revokeGrantId);
    const quantity = Number(revokeQuantity);
    const reference = revokeReference.trim();
    if (!source || !Number.isSafeInteger(quantity) || quantity < 1 || quantity > source.revocable_quantity
      || !reference || !revokePassword || !/^\d{6}$/.test(revokeTotp)) {
      setActionError("Selecione a concessão e informe quantidade, referência, senha atual e código de 6 dígitos do autenticador.");
      return;
    }
    const signature = JSON.stringify(["revoke", selectedTenant.tenant_id, source.id, quantity, reference]);
    setSaving("revoke");
    setActionError("");
    setActionMessage("");
    try {
      const response = await fetch(`/api/admin/platform/credit-grants/${source.id}/revoke`, {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId(signature),
          tenant_id: selectedTenant.tenant_id,
          quantity,
          reference,
          idempotency_key: idempotencyKey(signature),
          current_password: revokePassword,
          totp_code: revokeTotp,
        }),
      });
      await readJson<{ entry: CreditEntry; wallet: Wallet }>(response);
      idempotencyKeys.current.delete(signature);
      requestIds.current.delete(signature);
      setRevokeGrantId("");
      setRevokeQuantity("");
      setRevokeReference("");
      setRevokePassword("");
      setRevokeTotp("");
      setActionMessage("Revogação registrada e auditada na concessão de origem.");
      setRefreshVersion((value) => value + 1);
    } catch (error) {
      setRevokeTotp("");
      setActionError(error instanceof Error ? error.message : "Não foi possível revogar créditos.");
    } finally {
      setSaving(null);
    }
  }

  async function resolveFinancialReview(item: FinancialReview, decision: "release" | "restrict") {
    if (financialMutationInFlight) return;
    const reason = (reviewReasons[item.purchase_id] ?? "").trim();
    if (!reason || !reviewPassword || !/^\d{6}$/.test(reviewTotp)) {
      setReviewActionError("Informe a justificativa, sua senha atual e o código de 6 dígitos do autenticador.");
      return;
    }
    const signature = JSON.stringify([item.purchase_id, decision, reason]);
    let requestId = reviewRequestIds.current.get(signature);
    if (!requestId) {
      requestId = crypto.randomUUID();
      reviewRequestIds.current.set(signature, requestId);
    }
    setReviewingPurchaseId(item.purchase_id);
    setReviewActionError("");
    setReviewActionMessage("");
    try {
      const response = await fetch(`/api/admin/platform/credit-purchases/${item.purchase_id}/review`, {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId, decision, reason,
          current_password: reviewPassword, totp_code: reviewTotp }),
      });
      const updatedDetail = await readJson<TenantDetail>(response);
      reviewRequestIds.current.delete(signature);
      if (selectedTenantId === item.tenant_id) {
        setLoadedDetail(updatedDetail);
        setDetailTenantId(item.tenant_id);
        setDetailRefreshVersion(refreshVersion);
      }
      setReviewReasons((current) => ({ ...current, [item.purchase_id]: "" }));
      setReviewPassword("");
      setReviewTotp("");
      setReviewActionMessage(decision === "release"
        ? "Revisão registrada. Outros bloqueios financeiros continuam sendo avaliados separadamente."
        : "Revisão registrada e bloqueio mantido.");
      await loadReviewQueue();
      if (selectedTenantId === item.tenant_id) setRefreshVersion((value) => value + 1);
    } catch (error) {
      setReviewTotp("");
      setReviewActionError(error instanceof Error ? error.message : "Não foi possível registrar a revisão.");
    } finally {
      setReviewingPurchaseId(null);
    }
  }

  return (
    <SurfaceCard className={styles.card}>
      <div className={styles.heading}>
        <div>
          <p className="eyebrow">Proprietário da plataforma</p>
          <h2>Carteiras dos fotógrafos</h2>
          <p>Selecione uma conta para consultar saldo, movimentações e concessões disponíveis para revogação.</p>
        </div>
      </div>

      <section className={styles.reviewQueue} aria-label="Revisão financeira de compras contestadas">
        <div className={styles.reviewHeading}>
          <div>
            <p className="eyebrow">Ação do proprietário</p>
            <h3>Compras em revisão financeira</h3>
            <p>Estornos e chargebacks bloqueiam novos uploads e compras até uma decisão registrada.</p>
          </div>
          <StatusBadge tone={reviewQueue.length ? "warning" : "neutral"}>{reviewQueue.length} pendente(s)</StatusBadge>
        </div>
        {reviewActionError ? <p role="alert" className={styles.actionError}>{reviewActionError}</p> : null}
        {reviewActionMessage ? <p role="status" className={styles.actionMessage}>{reviewActionMessage}</p> : null}
        {reviewQueueState === "loading" ? (
          <SystemState tone="loading" title="Consultando revisões" detail="Buscando ocorrências financeiras abertas." />
        ) : reviewQueueState === "failed" ? (
          <SystemState tone="error" title="Fila de revisão indisponível" detail={reviewQueueError || "Não foi possível consultar as ocorrências."} />
        ) : reviewQueue.length ? (
          <>
          <div className={styles.reviewStepUp}>
            <label>Senha atual para revisão financeira<input type="password" autoComplete="current-password" required disabled={financialMutationInFlight} value={reviewPassword} onChange={(event) => setReviewPassword(event.target.value)} /></label>
            <label>Código do autenticador para revisão financeira<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={financialMutationInFlight} value={reviewTotp} onChange={(event) => setReviewTotp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
          </div>
          <ol className={styles.reviewItems}>
            {reviewQueue.map((item) => (
              <li key={item.purchase_id}>
                <div className={styles.reviewSummary}>
                  <strong>{item.photographer_email || "Fotógrafo sem e-mail ativo"}</strong>
                  <span>{item.package_name} · {item.credit_quantity} créditos · {formatPackagePrice(item.total_cents, item.currency_code)}</span>
                  <small>{item.payment_state === "charged_back" ? "Chargeback" : item.payment_state === "partially_refunded" ? "Reembolso parcial" : "Reembolso"}
                    {` · ${item.review_status === "restricted" ? "Bloqueio mantido" : "Aguardando decisão"} · ${formatDate(item.created_at)}`}</small>
                  <small>Tenant {item.tenant_id} · compra {item.purchase_id}</small>
                  {item.review_note ? <small>Última justificativa: {item.review_note}</small> : null}
                  {item.events.map((entry, index) => {
                    const reason = typeof entry.details.reason === "string" ? entry.details.reason : null;
                    const actor = typeof entry.details.actor_admin_id === "string" ? entry.details.actor_admin_id : null;
                    return entry.event_type === "owner_reviewed" ? (
                      <small key={`${entry.event_type}-${entry.occurred_at}-${index}`}>
                        Revisão anterior: {entry.details.decision === "release" ? "liberado" : "bloqueio mantido"}
                        {reason ? ` · ${reason}` : ""}{actor ? ` · proprietário ${actor}` : ""} · {formatDate(entry.occurred_at)}
                      </small>
                    ) : null;
                  })}
                </div>
                <label className={styles.reviewReason}>
                  Justificativa desta decisão
                  <textarea maxLength={500} required disabled={financialMutationInFlight} value={reviewReasons[item.purchase_id] ?? ""}
                    onChange={(event) => setReviewReasons((current) => ({ ...current, [item.purchase_id]: event.target.value }))} />
                </label>
                <div className={styles.reviewActions}>
                  <MarkinaButton type="button" disabled={financialMutationInFlight || !reviewReasons[item.purchase_id]?.trim() || !reviewPassword || !/^\d{6}$/.test(reviewTotp)}
                    onClick={() => void resolveFinancialReview(item, "release")}>
                    {reviewingPurchaseId === item.purchase_id ? "Registrando…" : "Liberar conta"}
                  </MarkinaButton>
                  <MarkinaButton type="button" variant="secondary" disabled={financialMutationInFlight || !reviewReasons[item.purchase_id]?.trim() || !reviewPassword || !/^\d{6}$/.test(reviewTotp)}
                    onClick={() => void resolveFinancialReview(item, "restrict")}>
                    Manter bloqueio
                  </MarkinaButton>
                </div>
              </li>
            ))}
          </ol>
          </>
        ) : (
          <SystemState title="Nenhuma compra aguardando revisão" detail="Novos estornos e chargebacks aparecerão aqui." />
        )}
      </section>

      <>
        <div className={styles.tenantPicker}>
          <div className={styles.tenantViewControls}>
            <label htmlFor="credit-tenant-view">
              Visualizar fotógrafos
              <select id="credit-tenant-view" disabled={financialMutationInFlight} value={tenantView}
                onChange={(event) => changeTenantSearch(searchQuery, event.target.value as TenantView)}>
                <option value="">Selecione</option>
                <option value="all">Todos</option>
                <option value="alphabetical">Ordem alfabética</option>
                <option value="recent">Mais recentes</option>
              </select>
            </label>
            <MarkinaButton type="button" variant="secondary" disabled={financialMutationInFlight}
              onClick={() => changeTenantSearch("", "")}>
              Limpar
            </MarkinaButton>
          </div>
          <label htmlFor="credit-tenant-search">Buscar fotógrafo pelo nome ou e-mail</label>
          <input
            id="credit-tenant-search"
            type="search"
            role="combobox"
            disabled={financialMutationInFlight}
            aria-autocomplete="list"
            aria-expanded={suggestionsOpen && listState === "ready" && tenants.length > 0}
            aria-controls={tenants.length > 0 ? "credit-tenant-suggestions" : undefined}
            aria-activedescendant={activeSuggestion >= 0 && tenants[activeSuggestion]
              ? `credit-tenant-option-${tenants[activeSuggestion].tenant_id}`
              : undefined}
            autoComplete="off"
            value={searchQuery}
            placeholder="Digite parte do nome ou e-mail"
            onChange={(event) => changeTenantSearch(event.target.value, tenantView)}
            onKeyDown={handleSearchKeyDown}
          />
          <span className={styles.searchHint}>Digite ao menos dois caracteres ou selecione uma opção. A ordem alfabética usa o nome quando disponível e o e-mail para perfis legados.</span>
        </div>

        {listState === "loading" ? (
          <SystemState tone="loading" title="Buscando fotógrafos" detail="Consultando sugestões autorizadas pelo proprietário." />
        ) : listState === "failed" ? (
          <SystemState tone="error" title="Busca de fotógrafos indisponível" detail="Não foi possível consultar as sugestões. Tente novamente pelo nome ou e-mail." />
        ) : null}

        {suggestionsOpen && listState === "ready" && tenants.length === 0 ? (
          <SystemState title="Nenhum fotógrafo encontrado" detail="Confira o nome ou o e-mail e tente novamente." />
        ) : null}

        {listState === "ready" && tenants.length > 0 ? (
          <ul className={styles.tenantSuggestions} id="credit-tenant-suggestions" role="listbox" aria-label="Sugestões de fotógrafos">
            {tenants.map((item, index) => (
              <li
                key={item.tenant_id}
                id={`credit-tenant-option-${item.tenant_id}`}
                role="option"
                aria-disabled={financialMutationInFlight}
                aria-selected={activeSuggestion === index}
                onMouseEnter={() => setActiveSuggestion(index)}
                onClick={() => selectTenant(item)}
              >
                <span>{tenantLabel(item)}</span>
                <small>{item.status === "active" ? "Ativo" : "Suspenso"}</small>
              </li>
            ))}
          </ul>
        ) : null}

        {suggestionsOpen && listState === "ready" && hasMoreTenants ? (
          <div className={styles.moreTenants}>
            <MarkinaButton type="button" variant="secondary" disabled={financialMutationInFlight || loadingMore}
              onClick={() => void loadMoreTenants()}>
              {loadingMore ? "Carregando mais…" : "Carregar mais"}
            </MarkinaButton>
          </div>
        ) : null}
        {moreError ? <p role="alert" className={styles.actionError}>{moreError}</p> : null}

          {selectedTenant ? (
            <>
              <div className={styles.tenantIdentity}>
                <div>
                  <strong>{tenantLabel(selectedTenant)}</strong>
                  <small>Tenant {selectedTenant.tenant_id}</small>
                </div>
                <StatusBadge tone={selectedTenant.status === "active" ? "success" : "warning"}>
                  {selectedTenant.status === "active" ? "Ativo" : "Suspenso"}
                </StatusBadge>
              </div>

              {currentDetailState === "loading" ? (
                <SystemState tone="loading" title="Consultando carteira" detail="Carregando saldo e histórico deste tenant." />
              ) : currentDetailState === "failed" || !detail ? (
                <SystemState tone="error" title="Detalhes da carteira indisponíveis" detail="O saldo e o histórico não foram tratados como zero." />
              ) : (
                <>
                  <section className={styles.metrics} aria-label="Resumo da carteira selecionada">
                    <MetricCard
                      label="Créditos disponíveis"
                      value={detail.wallet.mode === "unmetered" ? "Ilimitado" : detail.wallet.available_credits ?? "Indisponível"}
                      detail={detail.wallet.mode === "unmetered" ? "Conta do proprietário sem débito" : "Saldo confirmado pela API"}
                    />
                    <MetricCard
                      label={`Consumo nos últimos ${detail.wallet.recent_period_days} dias`}
                      value={detail.wallet.recent_consumed_credits}
                      detail={detail.wallet.mode === "unmetered" ? "Uploads não geram débito" : "Créditos de fotos armazenadas"}
                    />
                    <MetricCard
                      label="Operações pendentes"
                      value={detail.wallet.pending_operations}
                      detail={
                        String(detail.wallet.pending_upload_operations ?? detail.wallet.pending_operations)
                        + " upload(s) · " + String(detail.wallet.pending_recovery_operations ?? 0)
                        + " recuperação(ões) · " + String(detail.wallet.reserved_credits) + " crédito(s) reservado(s)"
                      }
                      tone={detail.wallet.pending_operations ? "warning" : "neutral"}
                    />
                  </section>

                  {detail.financial_reviews.length ? (
                    <section className={styles.financialHistory} aria-label="Histórico de revisões financeiras">
                      <div className={styles.historyHeading}>
                        <div><p className="eyebrow">Trilha financeira</p><h3>Compras contestadas e revisões</h3></div>
                        <StatusBadge>{detail.financial_reviews.length} registro(s)</StatusBadge>
                      </div>
                      <ol>
                        {detail.financial_reviews.map((item) => (
                          <li key={item.purchase_id}>
                            <div className={styles.reviewSummary}>
                              <strong>{item.package_name} · {item.credit_quantity} créditos · {formatPackagePrice(item.total_cents, item.currency_code)}</strong>
                              <span>{reviewStateLabel(item.payment_state)} · {item.review_status === "pending" ? "Aguardando decisão"
                                : item.review_status === "restricted" ? "Bloqueio mantido" : "Liberado após revisão"}</span>
                              <small>Compra {item.purchase_id} · {formatDate(item.created_at)}</small>
                              {item.review_note ? <small>Justificativa atual: {item.review_note}</small> : null}
                              {item.reviewed_by_admin_id && item.reviewed_at ? (
                                <small>Revisado pelo proprietário {item.reviewed_by_admin_id} · {formatDate(item.reviewed_at)}</small>
                              ) : null}
                              {item.events.map((entry, index) => {
                                const reason = typeof entry.details.reason === "string" ? entry.details.reason : null;
                                const actor = typeof entry.details.actor_admin_id === "string" ? entry.details.actor_admin_id : null;
                                return (
                                  <small key={`${entry.event_type}-${entry.occurred_at}-${index}`}>
                                    {entry.event_type === "owner_reviewed" ? "Decisão do proprietário" : reviewStateLabel(entry.event_type)}
                                    {entry.details.decision === "release" ? " · liberado" : entry.details.decision === "restrict" ? " · bloqueio mantido" : ""}
                                    {reason ? ` · ${reason}` : ""}{actor ? ` · proprietário ${actor}` : ""} · {formatDate(entry.occurred_at)}
                                  </small>
                                );
                              })}
                            </div>
                          </li>
                        ))}
                      </ol>
                    </section>
                  ) : null}

                  <OwnerMediaArchiveRecoveries
                    tenantId={selectedTenantId}
                    items={detail.media_archive_recoveries ?? []}
                    onUpdated={() => setRefreshVersion((value) => value + 1)}
                  />

                  {detail.wallet.mode === "unmetered" ? (
                    <SystemState title="Conta ilimitada do proprietário" detail="Esta carteira é somente para consulta. Concessões e revogações são aplicáveis às carteiras finitas dos fotógrafos." />
                  ) : detail.wallet.state === "unavailable" ? (
                    <SystemState tone="error" title="Carteira indisponível para operações" detail="Corrija a inconsistência antes de conceder ou revogar créditos." />
                  ) : (
                    <div className={styles.forms}>
                      <form className={styles.operationForm} onSubmit={grantCredits}>
                        <h3>Conceder créditos</h3>
                        <label>Quantidade<input type="number" min="1" step="1" required disabled={financialMutationInFlight} value={grantQuantity} onChange={(event) => setGrantQuantity(event.target.value)} /></label>
                        <label>Referência da concessão<input maxLength={240} required disabled={financialMutationInFlight} value={grantReference} onChange={(event) => setGrantReference(event.target.value)} /></label>
                        <label>Senha atual<input type="password" autoComplete="current-password" required disabled={financialMutationInFlight} value={grantPassword} onChange={(event) => setGrantPassword(event.target.value)} /></label>
                        <label>Código do autenticador<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={financialMutationInFlight} value={grantTotp} onChange={(event) => setGrantTotp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
                        <MarkinaButton disabled={financialMutationInFlight}>{saving === "grant" ? "Registrando…" : "Conceder créditos"}</MarkinaButton>
                      </form>

                      <form className={styles.operationForm} onSubmit={revokeCredits}>
                        <h3>Revogar créditos não utilizados</h3>
                        {activeGrantSources.length ? (
                          <>
                            <label>Concessão de origem
                               <select required disabled={financialMutationInFlight} value={revokeGrantId} onChange={(event) => {
                                setRevokeGrantId(event.target.value);
                                setRevokeQuantity("");
                              }}>
                                <option value="">Selecione uma concessão</option>
                                {activeGrantSources.map((grant) => (
                                  <option key={grant.id} value={grant.id}>
                                    {grant.revocable_quantity} livre(s) · {grant.source_reference || grant.id.slice(0, 8)} · {formatDate(grant.created_at)}
                                  </option>
                                ))}
                              </select>
                            </label>
                             <label>Quantidade<input type="number" min="1" max={activeGrantSources.find((grant) => grant.id === revokeGrantId)?.revocable_quantity} step="1" required disabled={financialMutationInFlight} value={revokeQuantity} onChange={(event) => setRevokeQuantity(event.target.value)} /></label>
                             <label>Referência da revogação<input maxLength={240} required disabled={financialMutationInFlight} value={revokeReference} onChange={(event) => setRevokeReference(event.target.value)} /></label>
                             <label>Senha atual<input type="password" autoComplete="current-password" required disabled={financialMutationInFlight} value={revokePassword} onChange={(event) => setRevokePassword(event.target.value)} /></label>
                             <label>Código do autenticador<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={financialMutationInFlight} value={revokeTotp} onChange={(event) => setRevokeTotp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
                             <MarkinaButton variant="secondary" disabled={financialMutationInFlight || !revokeGrantId}>{saving === "revoke" ? "Registrando…" : "Revogar créditos"}</MarkinaButton>
                          </>
                        ) : (
                          <SystemState title="Sem créditos livres para revogar" detail="Consumos e reservas continuam ligados à concessão original." />
                        )}
                      </form>
                    </div>
                  )}

                  {actionError ? <p role="alert" className={styles.actionError}>{actionError}</p> : null}
                  {actionMessage ? <p role="status" className={styles.actionMessage}>{actionMessage}</p> : null}

                  <CreditHistory
                    endpoint={`/api/admin/platform/credit-tenants/${selectedTenantId}/history`}
                    title="Movimentações recentes" label="Histórico financeiro do tenant" level={3} className={styles.history}
                    initialPage={detail.history ?? { items: detail.entries, has_more: false }}
                    refreshKey={`${selectedTenantId}:${refreshVersion}:${detail.history?.as_of ?? "legacy"}`}
                  />

                  <details className={styles.grantHistory}>
                    <summary>Ver origens FIFO e saldo revogável</summary>
                    {detail.revocable_grants.length ? (
                      <ul>
                        {detail.revocable_grants.map((grant) => (
                          <li key={grant.id}>
                            <span>{grant.source_reference || grant.id} · concedido em {formatDate(grant.created_at)}</span>
                            <strong>{grant.revocable_quantity} de {grant.quantity} crédito(s) disponível(is)</strong>
                          </li>
                        ))}
                      </ul>
                    ) : <p>Nenhuma concessão registrada.</p>}
                  </details>
                </>
              )}
            </>
          ) : null}
      </>
    </SurfaceCard>
  );
}
