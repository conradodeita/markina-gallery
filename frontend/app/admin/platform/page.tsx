"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { MarkinaButton, PageHeading, SurfaceCard, SystemState } from "../../ui-kit";
import { useConsoleAccess } from "./use-console-access";
import { PhotographerTotpSupport, supportReasonLabel } from "./photographer-totp-support";
import { PhotographerAccessRecovery } from "./photographer-access-recovery";
import recoveryStyles from "./photographer-access-recovery.module.css";
import { PhotographerTermsEditor } from "./photographer-terms-editor";
import { PhotographerTermsHistory } from "./photographer-terms-history";
import { TenantClosureConsole } from "./tenant-closure-console";
import { GoogleDriveConnectForm } from "./google-drive-connect";

type Tenant = { tenant_id: string; status: string; lifecycle: string; canonical_host: string | null; canonical_host_status: "reserved" | "ready" | null; photographer_name?: string | null; admin_email: string | null };
type Detail = Omit<Tenant, "admin_email"> & { gallery_count: number; photo_count: number; observed_at: string };
type Page = { items: Tenant[]; has_more: boolean; observed_at: string };
type Mode = "" | "all" | "alphabetical" | "recent";
type Audit = { id: string; action: string; result: string; created_at: string; reason_code?: string; evidence_sha256?: string };
const EXPECTED_SOURCE_KEYS = ["backup", "drive", "archive", "restore", "postgres_restore"] as const;

type Source = {
  key: string;
  state: string;
  availability: string;
  source: string | null;
  scope: string;
  observed_at: string | null;
  connection_updated_at?: string | null;
  quota_limit?: string | null;
  quota_usage?: string | null;
  quota_observed_at?: string | null;
  latest_run_status?: string | null;
  latest_attempt_day?: string | null;
  last_validated_day?: string | null;
  last_validated_at?: string | null;
  snapshot_id?: string | null;
  dump_size_bytes?: number | null;
  duration_ms?: number | null;
};

function formatBytes(value: string | number | null | undefined) {
  if (value == null || !/^\d+$/.test(String(value))) return "não informado";
  const bytes = Number(value);
  if (!Number.isSafeInteger(bytes)) return `${value} B`;
  const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
  let divisor = 1;
  let unit = 0;
  while (unit < units.length - 1 && bytes >= divisor * 1024) { divisor *= 1024; unit++; }
  if (unit === 0) return `${value} B`;
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(bytes / divisor)} ${units[unit]}`;
}

function formatDuration(value: number | null | undefined) {
  if (value == null || !Number.isSafeInteger(value) || value < 0) return "não informado";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value / 1000)} s`;
}

function backupStateLabel(source: Source) {
  if (source.state === "current") return "Cópia global validada hoje";
  if (source.state === "stale") return "A última cópia validada está desatualizada";
  if (source.state === "unavailable") return "Estado do backup indisponível";
  if (source.latest_run_status === "failed") return "A última tentativa falhou; nenhuma cópia atual foi validada";
  if (source.latest_run_status === "running") return "Cópia em andamento; validação ainda não concluída";
  return "Estado desconhecido; nenhuma cópia validada foi confirmada";
}

function sourceStateLabel(source: Source | undefined, subject: string) {
  if (source?.state === "current") return `${subject}: estado atual registrado`;
  if (source?.state === "stale") return `${subject}: estado desatualizado`;
  if (source?.state === "unavailable") return `${subject}: estado indisponível`;
  return `${subject}: estado desconhecido`;
}

function sourceOriginLabel(source: Source | undefined) {
  if (!source?.source) return "Origem não registrada";
  if (source.key === "archive") return "Origem: catálogo local do arquivo frio";
  if (source.key === "restore") return "Origem: registros locais de recuperação";
  return "Origem: registro local do serviço";
}

function sourceEvidenceDateLabel(source: Source | undefined) {
  const timestamp = source?.last_validated_at ?? source?.observed_at;
  if (typeof timestamp !== "string") return "Idade e evidência não informadas";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "Idade e evidência não informadas";
  return `${source?.last_validated_at ? "Última evidência" : "Estado observado"} em ${date.toLocaleString("pt-BR")}`;
}

function mediaRestoreOperationLabel(source: Source | undefined) {
  const labels: Record<string, string> = {
    queued: "aguardando processamento",
    processing: "em processamento",
    failed: "falha",
    reconciliation_required: "reconciliação necessária",
    completed: "concluída",
    cancelled: "cancelada",
  };
  if (!source?.latest_run_status) return null;
  return labels[source.latest_run_status] ?? "desconhecida";
}

function driveStateLabel(source: Source) {
  if (source.availability === "authorization_recorded") return "Autorização registrada";
  if (source.availability === "revoked") return "Autorização revogada";
  if (source.availability === "reauthorization_required") return "Nova autorização necessária";
  return "Nenhuma conexão registrada";
}

function lifecycleLabel(value: string) {
  if (value === "open") return "Aberta";
  if (value === "closing") return "Encerrando";
  if (value === "closed") return "Encerrada";
  return "Estado indisponível";
}

function auditActionLabel(action: string) {
  const labels: Record<string, string> = {
    "tenant.suspend": "Suspensão de conta", "tenant.activate": "Reativação de conta",
    "tenant.host_ready": "Liberação de endereço", "photographer.totp_revoked": "Revogação de autenticador",
    "tenant.reopened": "Reabertura de conta", "tenant.media_deletion_requested": "Exclusão de mídia",
    "tenant.media_deletion_retry": "Nova tentativa de exclusão de mídia",
    "tenant.profile_reduced": "Redução de CPF e endereço",
    "console.access_denied": "Acesso recusado", "tenant.status_denied": "Alteração recusada",
  };
  return labels[action] ?? "Ação administrativa";
}

export default function PlatformConsole() {
  const { access, revalidating } = useConsoleAccess();
  if (access === false) return <SystemState tone="error" title="Console indisponível" detail="É necessário acesso de proprietário da plataforma." />;
  return <>
    {access === null || revalidating ? <SystemState tone="loading" title="Verificando acesso" detail="Aguarde a confirmação da sua sessão." /> : null}
    {access === true ? <div hidden={revalidating} inert={revalidating}><ConsoleContent /></div> : null}
  </>;
}

function ConsoleContent() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("");
  const [page, setPage] = useState<Page | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sources, setSources] = useState<Source[] | null>(null);
  const [sourcesFailed, setSourcesFailed] = useState(false);
  const [audit, setAudit] = useState<Audit[] | null>(null);
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [hostnameHash, setHostnameHash] = useState("");
  const [hostnameConfirmed, setHostnameConfirmed] = useState(false);
  const [hostnamePassword, setHostnamePassword] = useState("");
  const [hostnameTotp, setHostnameTotp] = useState("");
  const pendingStatus = useRef<{ tenantId: string; status: string; expectedStatus: string; requestId: string } | null>(null);
  const pendingHostname = useRef<{ tenantId: string; hostname: string; hash: string; requestId: string } | null>(null);
  const request = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const applied = useRef({ query: "", mode: "" as Mode });

  useEffect(() => {
    const sourceController = new AbortController();
    const invalidate = () => { request.current++; controller.current?.abort(); };
    void fetch("/api/admin/platform/console/sources", {
      cache: "no-store", credentials: "same-origin", signal: sourceController.signal,
    }).then(async (response) => {
      if (!response.ok) throw new Error();
      const result = await response.json();
      if (!sourceController.signal.aborted) {
        const hasExpectedSources = Array.isArray(result.items)
          && result.items.length === EXPECTED_SOURCE_KEYS.length
          && EXPECTED_SOURCE_KEYS.every((key) => result.items.some((item: { key?: unknown }) => item?.key === key));
        if (hasExpectedSources) setSources(result.items as Source[]);
        else setSourcesFailed(true);
      }
    }).catch(() => { if (!sourceController.signal.aborted) setSourcesFailed(true); });
    return () => { sourceController.abort(); invalidate(); };
  }, []);

  async function load<T>(path: string, onData: (data: T) => void, init?: RequestInit) {
    const current = ++request.current;
    controller.current?.abort();
    controller.current = new AbortController();
    setBusy(true); setError(""); setDetail(null); setAudit(null);
    try {
      const response = await fetch(path, { ...init, credentials: "same-origin", cache: "no-store", signal: controller.current.signal });
      if (!response.ok) throw new Error(response.status === 403 || response.status === 401 ? "Acesso não autorizado. Atualize a página para verificar sua sessão." : response.status === 409 ? "O estado da conta mudou ou a operação não é permitida. Consulte novamente." : "Consulta indisponível. Tente novamente.");
      const result = await response.json();
      if (current === request.current) onData(result as T);
    } catch (failure) {
      if (current === request.current) {
        setPage(null); setDetail(null);
        setError(failure instanceof Error ? failure.message : "Consulta indisponível.");
      }
    } finally { if (current === request.current) setBusy(false); }
  }

  function clearConfirmationInputs() {
    setPassword(""); setTotp(""); setHostnameHash(""); setHostnameConfirmed(false);
    setHostnamePassword(""); setHostnameTotp("");
  }

  function consultTenant(tenantId: string) {
    clearConfirmationInputs();
    void load<Detail>(`/api/admin/platform/console/tenants/${tenantId}`, setDetail);
  }

  function search(nextOffset: number, submitted = false) {
    clearConfirmationInputs();
    if (submitted) applied.current = { query: query.trim(), mode };
    const filters = applied.current;
    setPage(null); setOffset(nextOffset);
    const params = new URLSearchParams({ q: filters.query, offset: String(nextOffset), limit: "10" });
    if (filters.mode) params.set("mode", filters.mode);
    void load(`/api/admin/platform/console/tenants?${params}`, setPage);
  }

  function submit(event: FormEvent) { event.preventDefault(); search(0, true); }

  function changeStatus(event: FormEvent) {
    event.preventDefault();
    if (!detail) return;
    const status = detail.status === "active" ? "suspended" : "active";
    const pending = pendingStatus.current;
    if (!pending || pending.tenantId !== detail.tenant_id || pending.expectedStatus !== detail.status || pending.status !== status) {
      pendingStatus.current = { tenantId: detail.tenant_id, expectedStatus: detail.status, status, requestId: crypto.randomUUID() };
    }
    const intent = pendingStatus.current!;
    const body = JSON.stringify({ request_id: intent.requestId, expected_status: intent.expectedStatus, status,
      current_password: password, totp_code: totp });
    setPassword(""); setTotp("");
    void load<{ status: string }>(`/api/admin/platform/console/tenants/${detail.tenant_id}/status`, () => {
      setPage(null); pendingStatus.current = null;
      void load<Detail>(`/api/admin/platform/console/tenants/${detail.tenant_id}`, setDetail);
    }, { method: "POST", headers: { "Content-Type": "application/json" }, body });
  }

  function activateHostname(event: FormEvent) {
    event.preventDefault();
    if (!detail?.canonical_host || detail.canonical_host_status !== "reserved") return;
    const hash = hostnameHash.trim().toLowerCase();
    const pending = pendingHostname.current;
    if (!pending || pending.tenantId !== detail.tenant_id || pending.hostname !== detail.canonical_host || pending.hash !== hash) {
      pendingHostname.current = { tenantId: detail.tenant_id, hostname: detail.canonical_host, hash, requestId: crypto.randomUUID() };
    }
    const intent = pendingHostname.current!;
    const body = JSON.stringify({ request_id: intent.requestId, expected_hostname: intent.hostname,
      expected_status: "reserved", evidence_sha256: intent.hash, confirm_readiness: hostnameConfirmed,
      current_password: hostnamePassword, totp_code: hostnameTotp });
    setHostnamePassword(""); setHostnameTotp("");
    void load<{ canonical_host_status: "ready" }>(`/api/admin/platform/console/tenants/${detail.tenant_id}/hostname/activate`, () => {
      pendingHostname.current = null; setHostnameHash(""); setHostnameConfirmed(false);
      void load<Detail>(`/api/admin/platform/console/tenants/${detail.tenant_id}`, setDetail);
    }, { method: "POST", headers: { "Content-Type": "application/json" }, body });
  }

  return <div className="mk-stack">
    <PageHeading eyebrow="Pick-your-Pic" title="Plataforma" detail="Contas de fotógrafos e acompanhamento da operação." />
    <SurfaceCard><h2>Fotógrafos</h2>
      <form onSubmit={submit}>
        <label>Nome ou e-mail do fotógrafo<input type="search" maxLength={320} value={query} onChange={(event) => setQuery(event.target.value)} /></label>
        <label>Organização<select value={mode} onChange={(event) => setMode(event.target.value as Mode)}>
          <option value="">Pesquisar por nome ou e-mail</option><option value="all">Todos</option>
          <option value="alphabetical">Ordem alfabética</option><option value="recent">Mais recentes</option>
        </select></label>
        <MarkinaButton disabled={busy || (!mode && query.trim().length < 2)}>Pesquisar</MarkinaButton>
      </form>
      {!page && !busy && !error ? <p>Pesquise um nome ou e-mail ou escolha uma organização para consultar as contas.</p> : null}
      {busy ? <p role="status">Consultando contas…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {page ? <><p>Consulta em {new Date(page.observed_at).toLocaleString("pt-BR")}</p>
        {page.items.length === 0 ? <p>Nenhuma conta encontrada.</p> : <ul>{page.items.map((item) => <li key={item.tenant_id}>
          <strong>{item.photographer_name || item.admin_email || "E-mail indisponível"}</strong>{item.photographer_name && item.admin_email ? <span> · {item.admin_email}</span> : null} · Disponibilidade: {item.status === "active" ? "Ativa" : "Suspensa"} · Encerramento: {lifecycleLabel(item.lifecycle)}
          <MarkinaButton variant="quiet" disabled={busy} onClick={() => consultTenant(item.tenant_id)}>Consultar {item.admin_email || "conta"}</MarkinaButton>
        </li>)}</ul>}
        <MarkinaButton variant="secondary" disabled={busy || offset === 0} onClick={() => search(Math.max(0, offset - 10))}>Anterior</MarkinaButton>
        <MarkinaButton variant="secondary" disabled={busy || !page.has_more} onClick={() => search(offset + 10)}>Próxima</MarkinaButton>
      </> : null}
    </SurfaceCard>
    {detail ? <SurfaceCard><h2>Resumo da conta</h2><p><strong>{detail.photographer_name || detail.tenant_id}</strong></p><p>Disponibilidade: {detail.status === "active" ? "Ativa" : "Suspensa"}</p><p>Encerramento: {lifecycleLabel(detail.lifecycle)}</p>
      <p>Galerias: {detail.gallery_count} · Fotografias: {detail.photo_count}</p>
      <p>Endereço do fotógrafo: {detail.canonical_host || "Não selecionado"}</p>
      {detail.canonical_host ? <p>Status do endereço: {detail.canonical_host_status === "ready" ? "Pronto para uso" : detail.canonical_host_status === "reserved" ? "Reservado; aguardando liberação" : "Endereço legado"}</p> : null}
      <small>Banco da aplicação · consulta da conta em {new Date(detail.observed_at).toLocaleString("pt-BR")}</small>
      <TenantClosureConsole key={`closure:${detail.tenant_id}`} tenantId={detail.tenant_id} onUpdated={() => consultTenant(detail.tenant_id)} />
      {detail.canonical_host && detail.canonical_host_status === "reserved" ? <form onSubmit={activateHostname}>
        <h3>Liberar endereço do fotógrafo</h3>
        <p>Revise o relatório de DNS, certificado e rota antes de liberar. Informe o SHA-256 do relatório revisado. O hash identifica o arquivo; ele não comprova sozinho o conteúdo.</p>
        <label>SHA-256 do relatório operacional<input type="text" inputMode="text" autoComplete="off" spellCheck={false} required minLength={64} maxLength={64} pattern="[0-9a-f]{64}" value={hostnameHash} onChange={(event) => setHostnameHash(event.target.value.toLowerCase())} /></label>
        <label><input type="checkbox" required checked={hostnameConfirmed} onChange={(event) => setHostnameConfirmed(event.target.checked)} />Confirmo que revisei o relatório para este endereço</label>
        <label>Senha do proprietário para esta liberação<input type="password" autoComplete="current-password" required maxLength={128} value={hostnamePassword} onChange={(event) => setHostnamePassword(event.target.value)} /></label>
        <label>Código do autenticador para esta liberação<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={hostnameTotp} onChange={(event) => setHostnameTotp(event.target.value)} /></label>
        <MarkinaButton disabled={busy || !/^[0-9a-f]{64}$/.test(hostnameHash)}>Confirmar liberação do endereço</MarkinaButton>
      </form> : null}
      {detail.canonical_host && detail.canonical_host_status === "ready" ? <p>Este endereço está liberado para uso.</p> : null}
      {detail.lifecycle !== "closed" ? <form className={`${recoveryStyles.panel} ${recoveryStyles.statusForm}`} onSubmit={changeStatus}>
        <h3>{detail.status === "active" ? "Suspender conta" : "Reativar conta"}</h3>
        <p>Suspender bloqueia acessos, uploads, processamento e mensagens. Os dados e a conciliação de pagamentos já iniciados são preservados.</p>
        <label>Senha atual<input type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <label>Código do autenticador<input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={totp} onChange={(event) => setTotp(event.target.value)} /></label>
        <label><input type="checkbox" required />Confirmo a alteração do estado desta conta</label>
        <MarkinaButton disabled={busy}>{detail.status === "active" ? "Confirmar suspensão" : "Confirmar reativação"}</MarkinaButton>
      </form> : <p>A conta encerrada não pode ser ativada pelo controle comum de disponibilidade. Use o fluxo de recuperação e reabertura acima.</p>}
      <PhotographerTotpSupport key={`totp-support:${detail.tenant_id}`} tenantId={detail.tenant_id} />
      <PhotographerAccessRecovery key={`access-recovery:${detail.tenant_id}`} tenantId={detail.tenant_id} />
    </SurfaceCard> : null}
    {detail ? <PhotographerTermsHistory key={detail.tenant_id} tenantId={detail.tenant_id} /> : null}
    <SurfaceCard><h2>Auditoria administrativa</h2><MarkinaButton variant="secondary" disabled={busy} onClick={() => void load<{ items: Audit[] }>("/api/admin/platform/console/audit", (result) => setAudit(result.items))}>Consultar ações recentes</MarkinaButton>
      {audit ? audit.length ? <ul>{audit.map((item) => <li key={item.id}>{new Date(item.created_at).toLocaleString("pt-BR")} · {auditActionLabel(item.action)} · {item.result === "success" ? "Concluída" : "Recusada"}{item.reason_code ? ` · ${supportReasonLabel(item.reason_code)}` : ""}{item.evidence_sha256 ? ` · SHA-256 ${item.evidence_sha256}` : ""}</li>)}</ul> : <p>Nenhuma ação registrada.</p> : null}
    </SurfaceCard>
    <SurfaceCard><h2>Créditos e compras</h2><p>Pacotes, carteiras e histórico de compras estão na área de créditos.</p><Link href="/admin/credits">Administrar créditos</Link></SurfaceCard>
    <PhotographerTermsEditor />
    <SurfaceCard><h2>Armazenamento externo e recuperação</h2>
      {sourcesFailed ? <p role="alert">Não foi possível consultar as fontes de acompanhamento.</p> : null}
      {!sources && !sourcesFailed ? <p role="status">Consultando registros de armazenamento…</p> : null}
      {sources ? <>
        {(() => {
          const drive = sources.find((item) => item.key === "drive");
          if (!drive) return <p>Registro do Google Drive indisponível.</p>;
          return <div>
            <h3>Google Drive</h3>
            <p>{driveStateLabel(drive)}</p>
            {drive.availability === "authorization_recorded"
              ? <p>Há uma autorização registrada. A disponibilidade atual do Drive não foi verificada.</p>
              : drive.availability === "revoked"
                ? <p>O registro informa que a autorização foi revogada. A disponibilidade atual do Drive não foi verificada.</p>
                : drive.availability === "reauthorization_required"
                  ? <p>O registro informa que é necessária uma nova autorização. A disponibilidade atual do Drive não foi verificada.</p>
                  : <p>Sem registro de conexão; quota desconhecida. A disponibilidade atual do Drive não foi verificada.</p>}
            {drive.quota_observed_at ? <p>Última quota registrada: {formatBytes(drive.quota_usage)} usados de {formatBytes(drive.quota_limit)} · consulta em {new Date(drive.quota_observed_at).toLocaleString("pt-BR")}</p> : <p>Quota ainda não observada.</p>}
            <small>{drive.connection_updated_at ? `Estado salvo em ${new Date(drive.connection_updated_at).toLocaleString("pt-BR")} · ` : ""}Registro consultado em {drive.observed_at ? new Date(drive.observed_at).toLocaleString("pt-BR") : "instante desconhecido"}</small>
            {drive.availability !== "authorization_recorded" ? <GoogleDriveConnectForm /> : null}
          </div>;
        })()}
        {(() => {
          const backup = sources.find((item) => item.key === "backup");
          if (!backup) return <p>Estado do backup global desconhecido.</p>;
          return <div>
            <h3>Backup global do PostgreSQL</h3>
            <p>{backupStateLabel(backup)}</p>
            {backup.last_validated_at ? <p>Último recibo validado: {backup.last_validated_day} · {new Date(backup.last_validated_at).toLocaleString("pt-BR")} · {formatBytes(backup.dump_size_bytes)} · {formatDuration(backup.duration_ms)}{backup.snapshot_id ? ` · Snapshot ${backup.snapshot_id.slice(0, 12)}` : ""}</p> : null}
            {backup.latest_run_status && backup.latest_run_status !== "validated" ? <p>Estado da tentativa mais recente: {backup.latest_run_status === "failed" ? "falha" : backup.latest_run_status === "running" ? "em andamento" : "desconhecido"}{backup.latest_attempt_day ? ` · ${backup.latest_attempt_day}` : ""}</p> : null}
            <small>Origem: recibos locais no PostgreSQL · estado observado em {backup.observed_at ? new Date(backup.observed_at).toLocaleString("pt-BR") : "instante desconhecido"}. Esta leitura não consulta a disponibilidade atual do destino remoto.</small>
          </div>;
        })()}
        {(() => {
          const restore = sources.find((item) => item.key === "postgres_restore");
          return <div>
            <h3>Recuperação global do PostgreSQL</h3>
            <p>{sourceStateLabel(restore, "Recuperação global do PostgreSQL")}</p>
            <p>{sourceOriginLabel(restore)}</p>
            <small>{sourceEvidenceDateLabel(restore)}. Nenhum restore é iniciado nesta consulta.</small>
          </div>;
        })()}
        {(() => {
          const archive = sources.find((item) => item.key === "archive");
          return <div>
            <h3>Arquivo frio de mídia</h3>
            <p>{sourceStateLabel(archive, "Arquivo frio de mídia")}</p>
            <p>{sourceOriginLabel(archive)}</p>
            <small>{sourceEvidenceDateLabel(archive)}</small>
          </div>;
        })()}
        {(() => {
          const restore = sources.find((item) => item.key === "restore");
          const operationStatus = mediaRestoreOperationLabel(restore);
          return <div>
            <h3>Recuperação de mídia</h3>
            <p>{sourceStateLabel(restore, "Recuperação de mídia")}</p>
            {operationStatus ? <p>Operação de recuperação registrada: {operationStatus}</p> : null}
            <p>{sourceOriginLabel(restore)}</p>
            <small>{sourceEvidenceDateLabel(restore)}. O registro local não confirma disponibilidade remota da mídia.</small>
          </div>;
        })()}
      </> : null}
    </SurfaceCard>
  </div>;
}
