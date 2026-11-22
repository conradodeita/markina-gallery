"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import styles from "./tenant-closure-panel.module.css";

type ClosureStatus = {
  lifecycle: "open" | "closing";
  credits_remaining: number;
  terms: { available: boolean; accepted: boolean; version: string | null; sha256: string | null };
  request: { requested_at: string; balance_snapshot: number } | null;
  blockers: { code: string; message: string }[];
};

export function PhotographerClosurePanel() {
  const [status, setStatus] = useState<ClosureStatus | null>(null);
  const [loadError, setLoadError] = useState("");
  const [message, setMessage] = useState("");
  const [confirmClosure, setConfirmClosure] = useState(false);
  const [acknowledgeBalance, setAcknowledgeBalance] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const requestId = useRef<string | null>(null);

  async function refresh(): Promise<ClosureStatus | null> {
    try {
      const response = await fetch("/api/admin/closure", {
        credentials: "same-origin", cache: "no-store",
      });
      if (!response.ok) throw new Error();
      const loaded = await response.json() as ClosureStatus;
      setStatus(loaded);
      setLoadError("");
      return loaded;
    } catch {
      setLoadError("Não foi possível consultar o estado da conta. Tente novamente.");
      return null;
    }
  }

  useEffect(() => {
    let cancelled = false;
    fetch("/api/admin/closure", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const loaded = await response.json() as ClosureStatus;
        if (!cancelled) {
          setStatus(loaded);
          setLoadError("");
        }
      })
      .catch(() => {
        if (!cancelled) setLoadError("Não foi possível consultar o estado da conta. Tente novamente.");
      });
    return () => { cancelled = true; };
  }, []);

  async function submit() {
    if (!status || !status.terms.version || !status.terms.sha256) return;
    setSubmitting(true);
    setMessage("");
    if (!requestId.current) requestId.current = window.crypto.randomUUID();
    try {
      const response = await fetch("/api/admin/closure", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: requestId.current,
          confirm_closure: true,
          acknowledge_remaining_balance: true,
          expected_balance: status.credits_remaining,
          terms_version: status.terms.version,
          terms_sha256: status.terms.sha256,
        }),
      });
      if (!response.ok) {
        if (response.status === 409) {
          requestId.current = null;
          const updated = await refresh();
          if (!updated || updated.credits_remaining !== status.credits_remaining) {
            setAcknowledgeBalance(false);
          }
          setMessage(!updated
            ? "A situação da conta mudou, mas não foi possível atualizá-la. Atualize a situação antes de tentar novamente."
            : updated.lifecycle === "closing"
              ? "A solicitação já está em andamento. Atualizei a situação para mostrar as pendências."
              : "A situação da conta mudou. Confira os dados atualizados antes de tentar novamente.");
        } else {
          setMessage("Não foi possível registrar o encerramento. Você pode tentar novamente.");
        }
        return;
      }
      requestId.current = null;
      setMessage("Solicitação registrada. O sistema acompanhará as pendências e atualizará esta página.");
      setConfirmClosure(false);
      setAcknowledgeBalance(false);
      await refresh();
    } catch {
      setMessage("Não foi possível registrar o encerramento. Você pode tentar novamente.");
    } finally {
      setSubmitting(false);
    }
  }

  return <section className={`mk-card ${styles.panel}`} aria-labelledby="photographer-closure-title">
    <div className={styles.heading}>
      <div>
        <p className="eyebrow">Conta do fotógrafo</p>
        <h2 id="photographer-closure-title">Encerramento da conta</h2>
      </div>
      {status ? <span className={styles.badge} data-state={status.lifecycle}>
        {status.lifecycle === "closing" ? "Encerrando" : "Ativa"}
      </span> : null}
    </div>

    {!status ? <div className={styles.feedback} role={loadError ? "alert" : "status"}>
      <p>{loadError || "Consultando o estado da conta…"}</p>
      {loadError ? <button type="button" className="mk-button mk-button--secondary" onClick={() => { setLoadError(""); void refresh(); }}>Tentar novamente</button> : null}
    </div> : status.lifecycle === "closing" ? <div className={styles.content}>
      <p className={styles.lead}>Sua solicitação foi recebida em {status.request?.requested_at
        ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" }).format(new Date(status.request.requested_at))
        : "data indisponível"}.</p>
      <p>Novas galerias e envios de fotos estão bloqueados. Galerias já publicadas permanecem acessíveis aos clientes dentro dos prazos informados. O encerramento será concluído depois que pedidos, pagamentos, outras obrigações e o processamento das mídias forem resolvidos.</p>
      <p className={styles.balance}>Saldo registrado no pedido: <strong>{status.request?.balance_snapshot ?? status.credits_remaining} créditos</strong>. O saldo e o histórico permanecem registrados; não há estorno manual.</p>
      {status.blockers.length ? <div>
        <h3>Pendências para concluir</h3>
        <ul className={styles.blockers}>{status.blockers.map((blocker, index) => <li key={`${blocker.code}-${index}`}>{blocker.message}</li>)}</ul>
      </div> : <p role="status">A checagem das etapas finais está em andamento. Atualize a situação para consultar novamente.</p>}
      <button type="button" className="mk-button mk-button--secondary" onClick={() => void refresh()}>Atualizar situação</button>
    </div> : <div className={styles.content}>
      <p>Você pode pedir o encerramento da sua conta. Antes de confirmar, confira o que acontecerá:</p>
      <ul className={styles.consequences}>
        <li>Novas galerias e envios de fotos serão bloqueados assim que o pedido for aceito.</li>
        <li>Galerias já publicadas continuarão acessíveis aos clientes dentro dos prazos informados.</li>
        <li>Pedidos, pagamentos e demais obrigações em andamento serão concluídos antes do encerramento definitivo.</li>
        <li>Créditos não utilizados não serão estornados; o saldo e o histórico financeiro permanecerão registrados.</li>
        <li>Depois de encerrada, você não poderá entrar na conta.</li>
      </ul>

      <div className={styles.balance} aria-live="polite">
        Saldo atual: <strong>{status.credits_remaining} créditos</strong>
      </div>

      {!status.terms.available ? <p className={styles.notice} role="status">Os Termos vigentes não estão disponíveis. Não é possível pedir o encerramento agora.</p>
        : !status.terms.accepted ? <p className={styles.notice}>Para continuar, aceite a versão vigente dos Termos em <Link href="/admin/settings#onboarding">Primeiros passos</Link>.</p>
          : <p className={styles.terms}>Termos vigentes aceitos: {status.terms.version}.</p>}

      <label className={styles.confirmation}>
        <input type="checkbox" checked={confirmClosure} onChange={(event) => setConfirmClosure(event.target.checked)} />
        <span>Confirmo que quero encerrar minha conta.</span>
      </label>
      <label className={styles.confirmation}>
        <input type="checkbox" checked={acknowledgeBalance} onChange={(event) => setAcknowledgeBalance(event.target.checked)} />
        <span>Reconheço que os {status.credits_remaining} créditos restantes e o histórico financeiro não serão estornados.</span>
      </label>
      <button type="button" className="mk-button mk-button--danger" onClick={() => void submit()}
        disabled={!status.terms.accepted || !status.terms.sha256 || !confirmClosure || !acknowledgeBalance || submitting}>
        {submitting ? "Enviando solicitação…" : "Solicitar encerramento"}
      </button>
    </div>}

    {status && loadError ? <div className={styles.feedback} role="alert">
      <p>{loadError}</p>
      <button type="button" className="mk-button mk-button--secondary" onClick={() => void refresh()}>
        Atualizar situação
      </button>
    </div> : null}

    {message ? <p className={styles.feedback} role="status">{message}</p> : null}
  </section>;
}
