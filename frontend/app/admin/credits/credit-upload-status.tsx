"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type CreditWalletSnapshot = {
  mode: "finite" | "unmetered";
  available_credits: number | null;
  reserved_credits: number;
  pending_operations: number;
  as_of?: string;
};

export type PhotoCreditStatus =
  | "uploading"
  | "reserved"
  | "reconciliation_required"
  | "consumed"
  | "released"
  | "not_charged"
  | "unmetered"
  | "confirmation_pending";

export type PhotoCreditItem = { photoId: string; filename: string; status: PhotoCreditStatus };

type WalletResponse = { wallet?: CreditWalletSnapshot; entries?: unknown[] };
type PhotoOperationResponse = {
  wallet?: CreditWalletSnapshot;
  operation?: { status?: string } | null;
};

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error("Não foi possível consultar o estado dos créditos.");
  return payload as T;
}

function isWallet(value: unknown): value is CreditWalletSnapshot {
  if (!value || typeof value !== "object") return false;
  const wallet = value as Partial<CreditWalletSnapshot>;
  return (wallet.mode === "finite" || wallet.mode === "unmetered")
    && Number.isInteger(wallet.reserved_credits)
    && Number.isInteger(wallet.pending_operations)
    && (wallet.mode === "unmetered" || Number.isInteger(wallet.available_credits));
}

const knownStatuses: PhotoCreditStatus[] = ["reserved", "reconciliation_required", "consumed", "released"];
const pendingStatuses: PhotoCreditStatus[] = ["uploading", "reserved", "reconciliation_required", "confirmation_pending"];

export function isDefinitiveUploadRejection(error: unknown) {
  if (!(error instanceof Error)) return false;
  const status = (error as Error & { httpStatus?: unknown }).httpStatus;
  return typeof status === "number" && status >= 400 && status < 500;
}

export function useCreditUploadStatus(enabled: boolean) {
  const [wallet, setWallet] = useState<CreditWalletSnapshot | null>(null);
  const [walletState, setWalletState] = useState<"loading" | "ready" | "failed">("loading");
  const [items, setItems] = useState<PhotoCreditItem[]>([]);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const readSequence = useRef<Record<string, number>>({});

  const setPhotoStatus = useCallback((photoId: string, filename: string, status: PhotoCreditStatus) => {
    setItems((current) => {
      const index = current.findIndex((item) => item.photoId === photoId);
      if (index >= 0 && current[index].filename === filename && current[index].status === status) return current;
      const next = [...current];
      const item = { photoId, filename, status };
      if (index >= 0) next[index] = item;
      else next.push(item);
      return next;
    });
  }, []);

  const startPhoto = useCallback((photoId: string, filename: string) => {
    readSequence.current[photoId] = (readSequence.current[photoId] ?? 0) + 1;
    setWalletState("loading");
    setPhotoStatus(photoId, filename, "uploading");
  }, [setPhotoStatus]);

  const refreshPhoto = useCallback(async (
    photoId: string, filename: string, definitiveRejection = false,
  ): Promise<PhotoCreditStatus> => {
    const sequence = (readSequence.current[photoId] ?? 0) + 1;
    readSequence.current[photoId] = sequence;
    try {
      const response = await fetch(`/api/admin/photo-assets/${photoId}/credit-operation`, {
        credentials: "same-origin", cache: "no-store",
      });
      const result = await readJson<PhotoOperationResponse>(response);
      if (readSequence.current[photoId] !== sequence) return "confirmation_pending";
      if (isWallet(result.wallet)) {
        setWallet((current) => {
          if (!current?.as_of || !result.wallet?.as_of) return result.wallet!;
          return Date.parse(current.as_of) > Date.parse(result.wallet.as_of) ? current : result.wallet;
        });
        setWalletState("ready");
      } else {
        setWalletState("failed");
      }
      const status = result.wallet?.mode === "unmetered"
        ? "unmetered"
        : knownStatuses.includes(result.operation?.status as PhotoCreditStatus)
          ? result.operation!.status as PhotoCreditStatus
          : definitiveRejection && result.wallet?.mode === "finite"
            ? "not_charged"
            : "confirmation_pending";
      setPhotoStatus(photoId, filename, status);
      return status;
    } catch {
      if (readSequence.current[photoId] !== sequence) return "confirmation_pending";
      setWalletState("failed");
      setPhotoStatus(photoId, filename, "confirmation_pending");
      return "confirmation_pending";
    }
  }, [setPhotoStatus]);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    fetch("/api/admin/credits/wallet", {
      credentials: "same-origin", cache: "no-store", signal: controller.signal,
    })
      .then((response) => readJson<WalletResponse>(response))
      .then((result) => {
        if (controller.signal.aborted) return;
        if (!isWallet(result.wallet)) throw new Error("Carteira inválida.");
        setWallet((current) => {
          if (!current?.as_of || !result.wallet?.as_of) return result.wallet!;
          return Date.parse(current.as_of) > Date.parse(result.wallet.as_of) ? current : result.wallet;
        });
        setWalletState("ready");
      })
      .catch(() => { if (!controller.signal.aborted) setWalletState("failed"); });
    return () => controller.abort();
  }, [enabled]);

  const pendingItems = items.filter((item) => pendingStatuses.includes(item.status));
  const pendingKey = pendingItems.map((item) => `${encodeURIComponent(item.photoId)}:${encodeURIComponent(item.filename)}`)
    .sort().join("|");

  useEffect(() => {
    if (!enabled || !pendingKey) return;
    let active = true;
    let timer: number | undefined;
    let attempts = 0;
    const itemsToPoll = pendingKey.split("|").map((value) => {
      const [photoId, filename] = value.split(":", 2).map(decodeURIComponent);
      return { photoId, filename };
    });
    const poll = async () => {
      await Promise.all(itemsToPoll.map((item) => refreshPhoto(item.photoId, item.filename)));
      attempts += 1;
      if (active && attempts < 60) timer = window.setTimeout(poll, 3000);
    };
    void poll();
    return () => { active = false; if (timer !== undefined) window.clearTimeout(timer); };
  }, [enabled, pendingKey, refreshNonce, refreshPhoto]);

  return {
    wallet,
    walletState,
    items,
    startPhoto,
    refreshPhoto,
    verifyPending: () => setRefreshNonce((value) => value + 1),
  };
}

function statusLabel(status: PhotoCreditStatus) {
  return {
    uploading: "Envio em andamento; aguardando confirmação da reserva.",
    reserved: "1 crédito reservado enquanto o arquivo é recebido.",
    reconciliation_required: "Confirmação pendente; o estado do arquivo está em reconciliação.",
    consumed: "1 crédito consumido, confirmado pelo servidor.",
    released: "Reserva liberada; o crédito voltou ao saldo disponível.",
    not_charged: "Nenhum crédito consumido; o servidor recusou o envio antes de criar uma operação.",
    unmetered: "A conta do proprietário é ilimitada; não há débito de créditos.",
    confirmation_pending: "Estado do crédito ainda não confirmado pelo servidor.",
  }[status];
}

export function CreditUploadFeedback({ wallet, walletState, items, visible = false, onVerifyPending }: {
  wallet: CreditWalletSnapshot | null;
  walletState: "loading" | "ready" | "failed";
  items: PhotoCreditItem[];
  visible?: boolean;
  onVerifyPending: () => void;
}) {
  if (!visible && !items.length) return null;
  const hasPending = items.some((item) => pendingStatuses.includes(item.status));
  return <section className="folder-upload-wallet" aria-label="Saldo de créditos durante o envio" aria-live="polite">
    <strong>{wallet?.mode === "unmetered" ? "Carteira ilimitada" : "Carteira de créditos"}</strong>
    {walletState !== "ready" || !wallet ? <span>{walletState === "failed" ? "Não foi possível consultar o saldo. Cada envio continua sendo autorizado pelo servidor." : "Consultando saldo e reservas…"}</span> : wallet.mode === "unmetered" ? <span>Envios ilimitados na conta do proprietário; nenhum débito finito é aplicado.</span> : <dl>
      <div><dt>Disponíveis</dt><dd>{wallet.available_credits ?? "Indisponível"}</dd></div>
      <div><dt>Reservados</dt><dd>{wallet.reserved_credits}</dd></div>
      <div><dt>Operações pendentes</dt><dd>{wallet.pending_operations}</dd></div>
    </dl>}
    {items.length ? <ul className="upload-credit-statuses" aria-label="Estado de créditos por arquivo">{items.map((item) => <li key={item.photoId}><span>{item.filename}</span><small>{statusLabel(item.status)}</small></li>)}</ul> : null}
    {hasPending ? <button type="button" className="link-button" onClick={onVerifyPending}>Verificar estado dos créditos</button> : null}
  </section>;
}
