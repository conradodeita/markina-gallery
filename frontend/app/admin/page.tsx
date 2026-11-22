"use client";

import { useEffect, useState } from "react";

import { CreditShortfallNotice } from "./credits/credit-shortfall-notice";
import {
  MarkinaLink,
  MetricCard,
  PageHeading,
  StatusBadge,
  SurfaceCard,
  SystemState,
} from "../ui-kit";

type Summary = {
  storage: {
    photo_count: number;
    bytes: number | null;
    available: boolean;
  };
  counts: {
    clients: number;
    parent_galleries: number;
    derived_galleries: number;
    imports: Record<string, number>;
    folders_with_active_imports: number;
    photos_in_folders_with_active_imports: number;
    folders_preparing?: number;
    folders_released?: number;
  };
  recent_galleries: Array<{
    id: string;
    name: string;
    active: boolean;
    event_name?: string | null;
  }>;
  recent_selections?: Array<{
    scope_id: string;
    client: { id: string; name: string };
    gallery: { id: string; name: string };
    parent_gallery: { id: string; name: string };
    selected_count: number;
    selection_started_at: string | null;
    last_selected_at: string;
  }>;
};

type CreditWallet = {
  mode: "finite" | "unmetered";
  available_credits: number | null;
  reserved_credits: number;
  pending_operations: number;
  recent_consumed_credits: number;
  recent_period_days: number;
  can_upload_content: boolean;
};

type CreditEntry = {
  id: string;
  type: string;
  delta: number;
  source_reference: string | null;
  description: string | null;
  created_at: string;
};

function creditEntryLabel(type: string): string {
  return {
    owner_grant: "Créditos concedidos",
    grant_revocation: "Créditos revogados",
    purchase: "Compra de créditos",
    upload_consumption: "Upload de foto",
    purchase_reversal: "Estorno de compra",
    correction: "Correção de saldo",
  }[type] ?? "Movimentação de créditos";
}

function formatCreditDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Data indisponível" : date.toLocaleString("pt-BR");
}

function selectionStartedLabel(value: string | null): string {
  if (!value) return "Horário não registrado";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Horário não registrado"
    : date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function formatStorage(bytes: number | null, available: boolean) {
  if (!available || bytes === null) return "Indisponível";
  const gibibyte = 1024 ** 3;
  const unit = bytes >= gibibyte ? "GB" : "MB";
  const divisor = unit === "GB" ? gibibyte : 1024 ** 2;
  const value = bytes === 0 ? 0 : bytes / divisor;
  return `${new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 1,
  }).format(value)} ${unit}`;
}

export default function AdminPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [failed, setFailed] = useState(false);
  const [wallet, setWallet] = useState<CreditWallet | null>(null);
  const [creditEntries, setCreditEntries] = useState<CreditEntry[]>([]);
  const [walletState, setWalletState] = useState<"loading" | "ready" | "failed">("loading");
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/admin/validation-summary", { credentials: "same-origin", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setSummary(await response.json());
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setFailed(true);
      });

    fetch("/api/admin/credits/wallet", {
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return response.json() as Promise<{ wallet: CreditWallet; entries: CreditEntry[] }>;
      })
      .then((result) => {
        setWallet(result.wallet);
        setCreditEntries(result.entries);
        setWalletState("ready");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setWalletState("failed");
      });
    return () => controller.abort();
  }, []);
  if (failed)
    return (
      <SystemState
        tone="error"
        title="Acesso administrativo indisponível"
        detail="Não foi possível carregar os dados. Recarregue a página para tentar novamente."
      />
    );
  if (!summary)
    return (
      <SystemState
        tone="loading"
        title="Preparando seu painel"
        detail="Consultando suas galerias e operações."
      />
    );
  const activeImportFolders = summary.counts.folders_with_active_imports;
  const photosInActiveImportFolders =
    summary.counts.photos_in_folders_with_active_imports;
  return (
    <div className="admin-dashboard">
      <PageHeading
        eyebrow="Central de operações"
        title="Seu próximo passo está à vista."
        detail="Acompanhe as galerias, conclua as pastas que estão em preparação e mantenha cada entrega no ritmo certo."
        actions={
          <>
            <MarkinaLink href="/admin/galleries/new">Nova galeria</MarkinaLink>
            <MarkinaLink href="/admin/galleries" variant="secondary">
              Ver galerias
            </MarkinaLink>
          </>
        }
      />
      <section className="dashboard-metrics">
        <MetricCard
          label="Galerias públicas"
          value={summary.counts.parent_galleries}
          detail="eventos sob seu controle"
        />
        <MetricCard
          label="Clientes"
          value={summary.counts.clients}
          detail="cadastros no sistema"
          tone="success"
        />
        <MetricCard
          label="Pastas com importação ativa"
          value={activeImportFolders}
          detail={`${photosInActiveImportFolders} ${photosInActiveImportFolders === 1 ? "foto nas" : "fotos nas"} pastas ativas`}
          tone={activeImportFolders ? "warning" : "success"}
        />
        <MetricCard
          label="Pastas liberadas"
          value={summary.counts.folders_released ?? 0}
          detail="visíveis a clientes autorizadas"
          tone="success"
        />
        <MetricCard
          label="Armazenamento de fotos"
          value={formatStorage(summary.storage.bytes, summary.storage.available)}
          detail={`${summary.storage.photo_count} ${
            summary.storage.photo_count === 1 ? "foto" : "fotos"
          }`}
          tone={summary.storage.available ? "neutral" : "warning"}
        />
      </section>
      <section className="dashboard-credit-section" aria-label="Carteira de créditos">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Créditos de fotografia</p>
            <h2>Carteira</h2>
            <p className="dashboard-section-detail">Saldo, uso recente e operações de upload desta conta.</p>
          </div>
          <MarkinaLink href="/admin/credits" variant="quiet">Ver carteira →</MarkinaLink>
        </div>
        {walletState === "loading" ? (
          <SystemState tone="loading" title="Consultando carteira" detail="Os dados operacionais continuam disponíveis enquanto o saldo é consultado." />
        ) : walletState === "failed" || !wallet ? (
          <SystemState tone="error" title="Saldo indisponível" detail="Não foi possível consultar a carteira. As métricas operacionais acima continuam disponíveis; o saldo não foi tratado como zero." />
        ) : (
          <>
            <div className="dashboard-metrics dashboard-credit-metrics">
              <MetricCard
                label="Créditos disponíveis"
                value={wallet.mode === "unmetered" ? "Ilimitado" : wallet.available_credits ?? "Indisponível"}
                detail={wallet.mode === "unmetered" ? "Conta do proprietário sem limite" : "Saldo informado pela API da carteira"}
              />
              <MetricCard
                label={`Consumo nos últimos ${wallet.recent_period_days} dias`}
                value={wallet.recent_consumed_credits}
                detail={wallet.mode === "unmetered" ? "Sua conta não recebe débito por uploads" : "Créditos usados em novos JPEGs de conteúdo"}
              />
              <MetricCard
                label="Uploads pendentes"
                value={wallet.pending_operations}
                detail={wallet.mode === "unmetered" ? "Operações aguardando conclusão" : `${wallet.reserved_credits} crédito(s) reservado(s)`}
                tone={wallet.pending_operations ? "warning" : "neutral"}
              />
            </div>
            {wallet.mode === "finite" && !wallet.can_upload_content ? (
              <CreditShortfallNotice />
            ) : null}
            <SurfaceCard>
              <div className="section-heading">
                <div><p className="eyebrow">Atividade financeira</p><h3>Movimentações recentes</h3></div>
              </div>
              {creditEntries.length ? (
                <div className="dashboard-credit-entries">
                  {creditEntries.slice(0, 5).map((entry) => (
                    <div key={entry.id}>
                      <div>
                        <strong>{entry.description || creditEntryLabel(entry.type)}</strong>
                        <small>{creditEntryLabel(entry.type)} · {formatCreditDate(entry.created_at)}</small>
                        {entry.source_reference ? <small>Origem: {entry.source_reference}</small> : null}
                      </div>
                      <b className={entry.delta < 0 ? "dashboard-credit-debit" : "dashboard-credit-credit"}>
                        {entry.delta > 0 ? "+" : ""}{entry.delta}
                      </b>
                    </div>
                  ))}
                </div>
              ) : (
                <SystemState title="Nenhuma movimentação" detail="Concessões e uploads cobrados aparecerão aqui." />
              )}
            </SurfaceCard>
          </>
        )}
      </section>
      <section className="dashboard-columns">
        <SurfaceCard>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Atenção agora</p>
              <h2>Prática de publicação</h2>
              <p className="dashboard-section-detail">
                Uma ordem simples para evitar liberar fotos incompletas.
              </p>
            </div>
          </div>
          <ol className="task-steps">
            <li>
              <b>1</b>
              <div>
                <strong>Contextualize a galeria</strong>
                <small>
                  Confira identidade, prazo e mensagem antes de adicionar fotos.
                </small>
              </div>
            </li>
            <li>
              <b>2</b>
              <div>
                <strong>Prepare uma pasta completa</strong>
                <small>
                  Envie JPEGs e revise as prévias antes de disponibilizar.
                </small>
              </div>
            </li>
            <li>
              <b>3</b>
              <div>
                <strong>Libere para as clientes certas</strong>
                <small>
                Vincule clientes e publique somente a rodada concluída.
                </small>
              </div>
            </li>
          </ol>
        </SurfaceCard>
        <SurfaceCard>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Acesso recente</p>
              <h2>Galerias recentes</h2>
            </div>
            <MarkinaLink href="/admin/galleries" variant="quiet">
              Todas →
            </MarkinaLink>
          </div>
          {summary.recent_galleries.length ? (
            <div className="dashboard-recent">
              {summary.recent_galleries.map((gallery) => (
                <div key={gallery.id}>
                  <div>
                    <MarkinaLink
                      href={`/admin/galleries/sources/${gallery.id}`}
                      variant="quiet"
                    >
                      {gallery.name}
                    </MarkinaLink>
                    <small>{gallery.event_name || "Galeria pública"}</small>
                  </div>
                  <StatusBadge
                    tone={gallery.active ? "success" : "danger"}
                  >
                    {gallery.active ? "Ativa" : "Bloqueada"}
                  </StatusBadge>
                </div>
              ))}
            </div>
          ) : (
            <SystemState
              title="Ainda não há galerias privadas"
              detail="Comece criando uma Galeria pública e vinculando uma cliente."
            />
          )}
          <div className="dashboard-open-selections">
            <div className="section-heading">
              <div>
                <h3>Clientes com seleção em andamento</h3>
                <p className="dashboard-section-detail">Horários exibidos no fuso local deste dispositivo.</p>
              </div>
            </div>
            {summary.recent_selections?.length ? (
              <div className="dashboard-recent">
                {summary.recent_selections.map((selection) => {
                  const params = new URLSearchParams({
                    client_id: selection.client.id,
                    parent_gallery_id: selection.parent_gallery.id,
                  });
                  const anchor = `open-selection-${selection.scope_id}-${selection.client.id}`;
                  return (
                    <div key={`${selection.scope_id}:${selection.client.id}`}>
                      <div>
                        <MarkinaLink
                          href={`/admin/payments?${params.toString()}#${anchor}`}
                          variant="quiet"
                        >
                          {selection.client.name}
                        </MarkinaLink>
                        <small>{selection.gallery.name} · {selection.parent_gallery.name}</small>
                        <small>{selection.selected_count} foto(s) · Iniciada em {selectionStartedLabel(selection.selection_started_at)}</small>
                      </div>
                      <StatusBadge tone="neutral">Em andamento</StatusBadge>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="dashboard-section-detail">Nenhuma cliente está selecionando fotos agora.</p>
            )}
          </div>
        </SurfaceCard>
      </section>
    </div>
  );
}
