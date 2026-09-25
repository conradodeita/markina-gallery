"use client";

import { FormEvent, useRef, useState } from "react";
import { MarkinaButton } from "../../ui-kit";
import { safeOrderAlbumUrl } from "../../order-album-url";

export type OrderDelivery = {
  album_url: string | null;
  version: number;
  updated_at?: string | null;
  can_send: boolean;
  can_resend: boolean;
};

export function OrderDeliveryForm({ orderId, delivery, onRefresh }: { orderId: string; delivery: OrderDelivery; onRefresh: () => Promise<void> }) {
  const [draft, setDraft] = useState(delivery.album_url ?? "");
  const [saved, setSaved] = useState(delivery);
  const [seen, setSeen] = useState(delivery);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const inFlight = useRef(false);
  const resendId = useRef<string | null>(null);
  // Reconciliar atualização ao foco sem descartar um rascunho não enviado.
  if (seen.version !== delivery.version || seen.can_send !== delivery.can_send || seen.album_url !== delivery.album_url) {
    setSeen(delivery); setSaved(delivery);
    if (draft.trim() === (seen.album_url ?? "")) setDraft(delivery.album_url ?? "");
  }
  const changed = draft.trim() !== (saved.album_url ?? "");

  async function submit(action: "send" | "remove" | "resend") {
    if (inFlight.current) return;
    if (action === "send" && !safeOrderAlbumUrl(draft.trim())) {
      setFailed(true); setMessage("Informe um link de compartilhamento HTTPS do Google Photos."); return;
    }
    if (action === "remove" && !window.confirm("Remover o link deste pedido? O botão ficará indisponível em Compras.")) return;
    if (action === "resend" && !window.confirm("Reenviar o aviso de fotos disponíveis para este pedido?")) return;
    inFlight.current = true; setBusy(true); setMessage(""); setFailed(false);
    try {
      if (action === "resend") resendId.current ??= crypto.randomUUID();
      const response = await fetch(`/api/admin/orders/${orderId}/delivery${action === "resend" ? "/resend" : ""}`, {
        method: action === "resend" ? "POST" : "PUT", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action === "resend" ? { version: saved.version, operation_id: resendId.current }
          : { album_url: action === "remove" ? null : draft.trim(), version: saved.version }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Não foi possível atualizar a entrega.");
      setSaved(data.delivery); setDraft(data.delivery.album_url ?? ""); resendId.current = null;
      setMessage(action === "remove" ? "Link removido. Fotos indisponíveis em Compras."
        : data.unchanged ? "Este link já está disponível. Use Reenviar aviso para notificar novamente."
          : data.notification?.channels?.length ? "Fotos disponíveis em Compras. Aviso agendado."
            : "Fotos disponíveis em Compras. Nenhum aviso agendado: confira os canais em Notificações e sua disponibilidade.");
      await onRefresh();
    } catch (error) {
      setFailed(true); setMessage(error instanceof Error && error.message !== "Failed to fetch" ? error.message : "Não foi possível atualizar a entrega. Tente novamente.");
    } finally { inFlight.current = false; setBusy(false); }
  }

  return <form className="order-delivery-form" aria-label="Entrega das fotos" onSubmit={(event: FormEvent) => { event.preventDefault(); void submit("send"); }}>
    <label htmlFor={`delivery-link-${orderId}`}>Link do álbum no Google Photos</label>
    <input id={`delivery-link-${orderId}`} type="url" maxLength={2048} value={draft} disabled={busy || !delivery.can_send}
      placeholder="https://photos.app.goo.gl/…" onChange={(event) => setDraft(event.target.value)} aria-describedby={`delivery-help-${orderId}`} />
    <p id={`delivery-help-${orderId}`}>{delivery.can_send ? "Enviar libera o álbum em Compras e avisa pelos canais habilitados em Notificações." : "Confirme o pagamento para disponibilizar as fotos."}</p>
    <div className="order-delivery-actions">
      <MarkinaButton type="submit" disabled={busy || !delivery.can_send || !draft.trim()}>{busy ? "Aguarde…" : "Enviar"}</MarkinaButton>
      {saved.album_url ? <>
        <MarkinaButton type="button" variant="secondary" disabled={busy || !delivery.can_send || changed} onClick={() => void submit("resend")}>Reenviar aviso</MarkinaButton>
        <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={() => void submit("remove")}>Remover link</MarkinaButton>
      </> : null}
    </div>
    {message ? <p role={failed ? "alert" : "status"}>{message}</p> : null}
  </form>;
}
