"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { mercadoPagoState, paymentMoney } from "../../library/mercadopago";
import { notifyPhotographerOnboardingGate } from "../../photographer-onboarding-gate";
import { MarkinaButton, MetricCard, PageHeading, StatusBadge, SurfaceCard, SystemState } from "../../ui-kit";
import { CreditShortfallNotice } from "./credit-shortfall-notice";
import CreditHistory from "./credit-history";
import CreditPurchaseCheckout, { type CreditPurchase } from "./credit-purchase-checkout";
import { MediaArchiveRecoveryPanel } from "./media-archive-recovery-panel";
import { OwnerCreditOperations } from "./owner-credit-operations";
import styles from "./credits.module.css";

type Wallet = {
  mode: "finite" | "unmetered";
  available_credits: number | null;
  reserved_credits: number;
  pending_operations: number;
  pending_upload_operations?: number;
  pending_recovery_operations?: number;
  recent_consumed_credits: number;
  recent_period_days: number;
  can_upload_content: boolean;
  financial_review_hold: boolean;
  financial_review_count: number;
  as_of: string;
};

type CreditPackage = {
  id: string;
  name: string;
  description: string | null;
  credit_quantity: number;
  price_cents: number | null;
  currency_code: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type PackageDraft = {
  name: string;
  description: string;
  credit_quantity: string;
  price_cents: string;
  currency_code: string;
  active: boolean;
};

type JsonRecord = Record<string, unknown>;

const blankDraft: PackageDraft = {
  name: "",
  description: "",
  credit_quantity: "",
  price_cents: "",
  currency_code: "",
  active: false,
};

async function readJson<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => null)) as JsonRecord | null;
  if (!response.ok) {
    notifyPhotographerOnboardingGate(payload?.detail);
    const detail = typeof payload?.detail === "string" ? payload.detail : "Não foi possível concluir a solicitação.";
    throw new Error(detail);
  }
  return payload as T;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

function formatPackagePrice(priceCents: number | null, currencyCode: string | null): string {
  if (priceCents === null || !currencyCode) return "Preço não configurado";
  try {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: currencyCode,
    }).format(priceCents / 100);
  } catch {
    return `${priceCents} centavos · ${currencyCode}`;
  }
}

export default function CreditsPage() {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [walletState, setWalletState] = useState<"loading" | "ready" | "failed">("loading");
  const [walletRefreshFailed, setWalletRefreshFailed] = useState(false);
  const [capabilityState, setCapabilityState] = useState<"loading" | "owner" | "photographer" | "failed">("loading");
  const [packages, setPackages] = useState<CreditPackage[]>([]);
  const [packageState, setPackageState] = useState<"loading" | "ready" | "failed">("loading");
  const [packageError, setPackageError] = useState("");
  const [purchases, setPurchases] = useState<CreditPurchase[]>([]);
  const [purchaseState, setPurchaseState] = useState<"loading" | "ready" | "failed">("loading");
  const [purchaseError, setPurchaseError] = useState("");
  const [selectedPurchase, setSelectedPurchase] = useState<CreditPurchase | null>(null);
  const [preparingPackageId, setPreparingPackageId] = useState<string | null>(null);
  const [purchaseActionMessage, setPurchaseActionMessage] = useState("");
  const [draft, setDraft] = useState<PackageDraft>(blankDraft);
  const [editingPackageId, setEditingPackageId] = useState<string | null>(null);
  const [savingPackage, setSavingPackage] = useState(false);
  const [packageMessage, setPackageMessage] = useState("");
  const [packagePassword, setPackagePassword] = useState("");
  const [packageTotp, setPackageTotp] = useState("");
  const packageRequestIds = useRef(new Map<string, string>());
  const purchaseRequestIds = useRef(new Map<string, string>());

  const loadPackages = useCallback(async (signal?: AbortSignal) => {
    setPackageState("loading");
    try {
      const response = await fetch("/api/admin/platform/credit-packages", {
        credentials: "same-origin",
        cache: "no-store",
        signal,
      });
      const result = await readJson<{ items: CreditPackage[] }>(response);
      setPackages(result.items);
      setPackageState("ready");
      setPackageError("");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setPackageError(error instanceof Error ? error.message : "Não foi possível carregar os pacotes.");
      setPackageState("failed");
    }
  }, []);

  const loadCatalogPackages = useCallback(async (signal?: AbortSignal) => {
    setPackageState("loading");
    try {
      const response = await fetch("/api/admin/credits/packages", {
        credentials: "same-origin",
        cache: "no-store",
        signal,
      });
      const result = await readJson<{ items: CreditPackage[] }>(response);
      setPackages(result.items);
      setPackageState("ready");
      setPackageError("");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setPackageError(error instanceof Error ? error.message : "Não foi possível carregar os pacotes.");
      setPackageState("failed");
    }
  }, []);

  const loadWallet = useCallback(async (signal?: AbortSignal) => {
    const response = await fetch("/api/admin/credits/wallet", {
      credentials: "same-origin",
      cache: "no-store",
      signal,
    });
    const result = await readJson<{ wallet: Wallet }>(response);
    setWallet(result.wallet);
    setWalletRefreshFailed(false);
    setWalletState("ready");
  }, []);

  const refreshWalletAfterRecovery = useCallback(() => {
    void loadWallet().catch(() => setWalletRefreshFailed(true));
  }, [loadWallet]);

  const loadPurchases = useCallback(async (signal?: AbortSignal) => {
    setPurchaseState("loading");
    try {
      const [historyResponse, activeResponse] = await Promise.all([
        fetch("/api/admin/credits/purchases?limit=20", {
          credentials: "same-origin", cache: "no-store", signal,
        }),
        fetch("/api/admin/credits/purchases/active", {
          credentials: "same-origin", cache: "no-store", signal,
        }),
      ]);
      const [history, active] = await Promise.all([
        readJson<{ items: CreditPurchase[] }>(historyResponse),
        readJson<{ items: CreditPurchase[] }>(activeResponse),
      ]);
      setPurchases(history.items);
      setSelectedPurchase((current) => current ?? active.items[0] ?? null);
      setPurchaseState("ready");
      setPurchaseError("");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setPurchaseError(error instanceof Error ? error.message : "Não foi possível carregar suas compras.");
      setPurchaseState("failed");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // A resposta assíncrona do endpoint hidrata a tela; não há setState antes da rede.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadWallet(controller.signal)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setWalletState("failed");
      });

    fetch("/api/admin/credits/capabilities", {
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
    })
      .then((response) => readJson<{ manage_packages: boolean }>(response))
      .then((result) => {
        if (result.manage_packages) {
          setCapabilityState("owner");
          void loadPackages(controller.signal);
        } else {
          setCapabilityState("photographer");
          void loadCatalogPackages(controller.signal);
          void loadPurchases(controller.signal);
        }
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setCapabilityState("failed");
      });

    return () => controller.abort();
  }, [loadCatalogPackages, loadPackages, loadPurchases, loadWallet]);

  async function prepareCreditPurchase(item: CreditPackage) {
    if (preparingPackageId) return;
    let idempotencyKey = purchaseRequestIds.current.get(item.id);
    if (!idempotencyKey) {
      idempotencyKey = crypto.randomUUID();
      purchaseRequestIds.current.set(item.id, idempotencyKey);
    }
    setPreparingPackageId(item.id);
    setPurchaseActionMessage("");
    try {
      const response = await fetch("/api/admin/credits/purchases/prepare", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ package_id: item.id, idempotency_key: idempotencyKey }),
      });
      const purchase = await readJson<CreditPurchase>(response);
      purchaseRequestIds.current.delete(item.id);
      setSelectedPurchase(purchase);
      setPurchases((current) => [purchase, ...current.filter((entry) => entry.id !== purchase.id)].slice(0, 20));
      setPurchaseState("ready");
    } catch (error) {
      setPurchaseActionMessage(error instanceof Error ? error.message : "Não foi possível preparar a compra.");
    } finally {
      setPreparingPackageId(null);
    }
  }

  function updatePurchase(purchase: CreditPurchase) {
    setSelectedPurchase(purchase);
    setPurchases((current) => [purchase, ...current.filter((entry) => entry.id !== purchase.id)]
      .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at)).slice(0, 20));
    if (purchase.state === "confirmed") {
      void loadWallet().catch(() => setWalletRefreshFailed(true));
    }
  }

  function startEditing(item: CreditPackage) {
    setEditingPackageId(item.id);
    setDraft({
      name: item.name,
      description: item.description ?? "",
      credit_quantity: String(item.credit_quantity),
      price_cents: item.price_cents === null ? "" : String(item.price_cents),
      currency_code: item.currency_code ?? "",
      active: item.active,
    });
    setPackageMessage("");
  }

  function resetDraft() {
    setEditingPackageId(null);
    setDraft(blankDraft);
    setPackagePassword("");
    setPackageTotp("");
  }

  async function savePackage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingPackage(true);
    setPackageMessage("");
    const quantity = Number(draft.credit_quantity);
    const price = draft.price_cents.trim() ? Number(draft.price_cents) : null;
    const currency = draft.currency_code.trim().toUpperCase() || null;
    if (!Number.isSafeInteger(quantity) || quantity < 1) {
      setPackageMessage("Informe uma quantidade inteira de créditos maior que zero.");
      setSavingPackage(false);
      return;
    }
    if (price !== null && (!Number.isSafeInteger(price) || price < 1)) {
      setPackageMessage("Informe o preço em centavos como um inteiro maior que zero.");
      setSavingPackage(false);
      return;
    }
    if (!packagePassword || !/^\d{6}$/.test(packageTotp)) {
      setPackageMessage("Informe sua senha atual e o código de 6 dígitos do autenticador.");
      setSavingPackage(false);
      return;
    }
    const intent = {
      name: draft.name,
      description: draft.description.trim() || null,
      credit_quantity: quantity,
      price_cents: price,
      currency_code: currency,
      active: draft.active,
    };
    const signature = JSON.stringify([editingPackageId ? "update" : "create", editingPackageId, intent]);
    let requestId = packageRequestIds.current.get(signature);
    if (!requestId) {
      requestId = crypto.randomUUID();
      packageRequestIds.current.set(signature, requestId);
    }
    try {
      const response = await fetch(editingPackageId
        ? `/api/admin/platform/credit-packages/${editingPackageId}`
        : "/api/admin/platform/credit-packages", {
        method: editingPackageId ? "PUT" : "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...intent,
          request_id: requestId,
          current_password: packagePassword,
          totp_code: packageTotp,
        }),
      });
      await readJson<CreditPackage>(response);
      packageRequestIds.current.delete(signature);
      setPackagePassword("");
      setPackageTotp("");
      setPackageMessage(editingPackageId ? "Pacote atualizado." : "Pacote criado como configurado.");
      resetDraft();
      await loadPackages();
    } catch (error) {
      setPackageTotp("");
      setPackageMessage(error instanceof Error ? error.message : "Não foi possível salvar o pacote.");
    } finally {
      setSavingPackage(false);
    }
  }

  return (
    <div className={styles.page}>
      <PageHeading
        eyebrow="Carteira"
        title="Créditos de fotografia"
        detail="Acompanhe o saldo da sua conta e as movimentações relacionadas aos uploads de conteúdo."
      />

      {walletState === "loading" ? (
        <SystemState tone="loading" title="Consultando carteira" detail="Buscando o saldo privado da sua conta." />
      ) : walletState === "failed" || !wallet ? (
        <SystemState tone="error" title="Saldo indisponível" detail="Não foi possível consultar a carteira. Os créditos não estão sendo tratados como zero." />
      ) : (
        <>
          {walletRefreshFailed ? (
            <>
              <SystemState tone="error" title="Saldo aguardando atualização"
                detail="Não foi possível atualizar o saldo e o histórico após a operação. O saldo anterior está oculto até uma nova consulta." />
              <MarkinaButton type="button" variant="secondary"
                onClick={() => void loadWallet().catch(() => setWalletRefreshFailed(true))}>
                Atualizar saldo
              </MarkinaButton>
            </>
          ) : (
          <section className={styles.metrics} aria-label="Resumo da carteira">
            <MetricCard
              label="Créditos disponíveis"
              value={wallet.mode === "unmetered" ? "Ilimitado" : wallet.available_credits ?? "Indisponível"}
              detail={wallet.mode === "unmetered" ? "Conta do proprietário sem limite" : "Prontos para novos uploads de conteúdo"}
            />
            <MetricCard
              label={`Consumo nos últimos ${wallet.recent_period_days} dias`}
              value={wallet.recent_consumed_credits}
              detail={wallet.mode === "unmetered" ? "Sua conta não recebe débito por uploads" : "Créditos usados em novos JPEGs de conteúdo"}
            />
            <MetricCard
              label="Créditos reservados"
              value={wallet.mode === "unmetered" ? "—" : wallet.reserved_credits}
              detail={wallet.pending_operations
                ? String(wallet.pending_upload_operations ?? wallet.pending_operations) + " upload(s) e "
                  + String(wallet.pending_recovery_operations ?? 0) + " recuperação(ões) em andamento"
                : "Nenhuma operação de crédito pendente"}
              tone={wallet.pending_operations ? "warning" : "neutral"}
            />
          </section>
          )}

          {!walletRefreshFailed && (wallet.financial_review_hold ? (
            <SystemState tone="error" title="Conta bloqueada para revisão financeira"
              detail="O proprietário está revisando uma ocorrência de pagamento. Novos uploads e compras ficam pausados até a decisão." />
          ) : wallet.mode === "finite" && !wallet.can_upload_content ? (
            <CreditShortfallNotice />
          ) : null)}

          <MediaArchiveRecoveryPanel onWalletChange={refreshWalletAfterRecovery} />

          {capabilityState === "photographer" ? (
            <SurfaceCard className={`${styles.card} ${styles.catalog}`}>
              <div className={styles.sectionHeading}>
                <div>
                  <p className="eyebrow">Créditos para fotógrafo</p>
                  <h2 id="credit-packages">Pacotes disponíveis</h2>
                  <p>Consulte os pacotes publicados pelo proprietário para novos envios de conteúdo.</p>
                </div>
              </div>

              {packageState === "loading" ? (
                <SystemState tone="loading" title="Carregando pacotes" detail="Consultando o catálogo disponível para sua conta." />
              ) : packageState === "failed" ? (
                <SystemState tone="error" title="Catálogo indisponível" detail={packageError || "Não foi possível carregar os pacotes."} />
              ) : packages.length ? (
                <>
                  <div className={styles.catalogGrid}>
                    {packages.map((item) => (
                      <article className={styles.catalogPackage} key={item.id}
                        data-selected={selectedPurchase?.package_id === item.id}>
                        <div className={styles.catalogPackageTop}>
                          <span className={styles.catalogKicker}>Pacote de créditos</span>
                          <span className={styles.catalogProvider}>Mercado Pago</span>
                        </div>
                        <h3>{item.name}</h3>
                        {item.description ? <p className={styles.catalogDescription}>{item.description}</p> : null}
                        <div className={styles.catalogQuantity}>
                          <strong>{new Intl.NumberFormat("pt-BR").format(item.credit_quantity)}</strong>
                          <span>créditos</span>
                        </div>
                        <div className={styles.catalogPrice}>
                          <span>Preço do pacote</span>
                          <strong>{formatPackagePrice(item.price_cents, item.currency_code)}</strong>
                        </div>
                        <MarkinaButton type="button" className={styles.catalogAction}
                          disabled={preparingPackageId !== null || walletRefreshFailed || wallet.financial_review_hold
                            || item.currency_code !== "BRL" || item.price_cents === null}
                          onClick={() => void prepareCreditPurchase(item)}>
                          {preparingPackageId === item.id ? "Preparando checkout…"
                            : item.currency_code === "BRL" ? "Comprar pacote"
                              : "Moeda indisponível para compra"}
                        </MarkinaButton>
                      </article>
                    ))}
                  </div>
                  <p className={styles.catalogNote}>
                    Pagamento protegido pelo Mercado Pago dentro da plataforma.
                  </p>
                  {purchaseActionMessage ? <p role="alert" className={styles.purchaseError}>{purchaseActionMessage}</p> : null}
                </>
              ) : (
                <SystemState title="Nenhum pacote disponível" detail="Os pacotes publicados pelo proprietário aparecerão aqui." />
              )}
            </SurfaceCard>
          ) : null}

          {capabilityState === "photographer" && selectedPurchase ? (
            <CreditPurchaseCheckout key={selectedPurchase.id} purchase={selectedPurchase} onClose={() => setSelectedPurchase(null)}
              onUpdated={updatePurchase} />
          ) : null}

          {capabilityState === "photographer" ? (
            <SurfaceCard className={styles.card}>
              <div className={styles.sectionHeading}>
                <div>
                  <p className="eyebrow">Pedidos</p>
                  <h2>Compras de créditos</h2>
                  <p>Confira o andamento dos pagamentos e retome uma compra pendente.</p>
                </div>
                <StatusBadge>{purchases.length} registro(s)</StatusBadge>
              </div>
              {purchaseState === "loading" ? (
                <SystemState tone="loading" title="Consultando compras" detail="Buscando o histórico privado desta conta." />
              ) : purchaseState === "failed" ? (
                <SystemState tone="error" title="Histórico indisponível" detail={purchaseError || "Não foi possível carregar suas compras."} />
              ) : purchases.length ? (
                <ol className={styles.entries}>
                  {purchases.map((purchase) => (
                    <li key={purchase.id}>
                      <div>
                        <strong>{purchase.package_name} · {new Intl.NumberFormat("pt-BR").format(purchase.credit_quantity)} créditos</strong>
                        <span>{paymentMoney(purchase.total_cents)} · {mercadoPagoState[purchase.state] ?? "Compra em conferência"} · {formatDate(purchase.created_at)}</span>
                        <small>Compra {purchase.id.slice(0, 8)} · Mercado Pago{purchase.method === "pix" ? " · PIX" : purchase.method === "credit_card" ? " · cartão" : ""}</small>
                      </div>
                      {purchase.active ? <MarkinaButton type="button" variant="secondary"
                        onClick={() => setSelectedPurchase(purchase)}>
                        {purchase.state === "prepared" ? "Retomar checkout" : "Ver pagamento"}
                      </MarkinaButton> : <StatusBadge tone={purchase.state === "confirmed" ? "success" : "neutral"}>
                        {mercadoPagoState[purchase.state] ?? "Atualizada"}
                      </StatusBadge>}
                    </li>
                  ))}
                </ol>
              ) : (
                <SystemState title="Nenhuma compra de créditos" detail="Depois de adquirir um pacote, seu pagamento aparecerá aqui." />
              )}
            </SurfaceCard>
          ) : null}

          {!walletRefreshFailed ? <SurfaceCard className={styles.card}>
            <CreditHistory endpoint="/api/admin/credits/history" refreshKey={wallet.as_of} />
          </SurfaceCard> : null}
        </>
      )}

      {capabilityState === "loading" ? (
        <SystemState tone="loading" title="Verificando recursos de gestão" detail="As opções aparecem conforme a autorização global da conta." />
      ) : capabilityState === "failed" ? (
        <SystemState tone="error" title="Permissões de gestão indisponíveis" detail="A carteira continua separada; não foi possível consultar os recursos administrativos." />
      ) : capabilityState === "owner" ? (
        <>
        <SurfaceCard className={styles.card}>
          <div className={styles.sectionHeading}>
            <div>
              <p className="eyebrow">Proprietário da plataforma</p>
              <h2>Pacotes de créditos</h2>
                <p>Defina quantidade, preço e moeda dos pacotes oferecidos aos fotógrafos. A compra usa a conta Mercado Pago configurada pelo proprietário.</p>
            </div>
          </div>

          {packageState === "loading" ? (
            <SystemState tone="loading" title="Carregando pacotes" detail="Consultando o catálogo global." />
          ) : packageState === "failed" ? (
            <SystemState tone="error" title="Catálogo indisponível" detail={packageError || "Não foi possível carregar os pacotes."} />
          ) : (
            <>
              {packages.length ? (
                <div className={styles.packageList}>
                  {packages.map((item) => (
                    <article className={styles.package} key={item.id}>
                      <div>
                        <StatusBadge tone={item.active ? "success" : "neutral"}>{item.active ? "Ativo" : "Inativo"}</StatusBadge>
                        <h3>{item.name}</h3>
                        {item.description ? <p>{item.description}</p> : null}
                        <dl>
                          <div><dt>Créditos</dt><dd>{item.credit_quantity}</dd></div>
                          <div><dt>Preço</dt><dd>{formatPackagePrice(item.price_cents, item.currency_code)}</dd></div>
                        </dl>
                      </div>
                      <MarkinaButton type="button" variant="secondary" onClick={() => startEditing(item)}>Editar pacote</MarkinaButton>
                    </article>
                  ))}
                </div>
              ) : (
                <SystemState title="Nenhum pacote configurado" detail="Crie um pacote quando decidir a quantidade e as condições comerciais." />
              )}

              <form className={styles.packageForm} onSubmit={savePackage} aria-label={editingPackageId ? "Editar pacote de créditos" : "Criar pacote de créditos"}>
                <h3>{editingPackageId ? "Editar pacote" : "Criar pacote"}</h3>
                <div className={styles.formGrid}>
                  <label>Nome do pacote<input required maxLength={120} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
                  <label>Quantidade de créditos<input required type="number" min="1" step="1" value={draft.credit_quantity} onChange={(event) => setDraft({ ...draft, credit_quantity: event.target.value })} /></label>
                  <label>Preço em centavos (opcional)<input type="number" min="1" step="1" value={draft.price_cents} onChange={(event) => setDraft({ ...draft, price_cents: event.target.value })} /></label>
                  <label>Moeda ISO (opcional)<input maxLength={3} autoCapitalize="characters" value={draft.currency_code} onChange={(event) => setDraft({ ...draft, currency_code: event.target.value.toUpperCase() })} /></label>
                  <label className={styles.descriptionField}>Descrição (opcional)<textarea maxLength={500} rows={3} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
                  <label className={styles.activeField}><input type="checkbox" checked={draft.active} onChange={(event) => setDraft({ ...draft, active: event.target.checked })} /> Ativar pacote</label>
                  <label>Senha atual para alterar pacote<input type="password" autoComplete="current-password" required value={packagePassword} onChange={(event) => setPackagePassword(event.target.value)} /></label>
                  <label>Código do autenticador para alterar pacote<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required value={packageTotp} onChange={(event) => setPackageTotp(event.target.value.replace(/\D/g, "").slice(0, 6))} /></label>
                </div>
                {packageMessage ? <p className={styles.formMessage} role="status">{packageMessage}</p> : null}
                <div className={styles.formActions}>
                  <MarkinaButton disabled={savingPackage}>{savingPackage ? "Salvando…" : editingPackageId ? "Salvar alterações" : "Criar pacote"}</MarkinaButton>
                  {editingPackageId ? <MarkinaButton type="button" variant="secondary" disabled={savingPackage} onClick={resetDraft}>Cancelar edição</MarkinaButton> : null}
                </div>
              </form>
            </>
          )}
        </SurfaceCard>
        <OwnerCreditOperations />
        </>
      ) : null}
    </div>
  );
}
