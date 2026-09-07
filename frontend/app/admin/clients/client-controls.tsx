"use client";

import { type FormEvent, useRef, useState } from "react";
import Link from "next/link";

import { MarkinaButton } from "../../ui-kit";

export type ClientDirectoryItem = {
  id: string;
  name: string;
  phone: string;
  aggregates?: {
    public_galleries: number;
    private_galleries: number;
    orders: number;
  };
  deletion_eligible?: boolean;
};

export type ClientDeletionInventory = {
  client_id: string;
  operational_removable: Record<string, number>;
  commercial_protected: Record<string, number>;
  can_delete: boolean;
};

const inventoryLabels: Record<string, string> = {
  client: "cadastro",
  phone_records: "telefone(s)",
  gallery_accesses: "acesso(s)",
  public_gallery_registrations: "vínculo(s) com Galeria pública",
  private_galleries_exclusive: "galeria(s) privada(s) exclusiva(s)",
  private_galleries_shared: "galeria(s) privada(s) compartilhada(s)",
  private_gallery_memberships: "vínculo(s) privado(s)",
  gallery_capabilities: "convite(s) e link(s)",
  selections: "seleção(ões)",
  favorites: "favorito(s)",
  views: "visualização(ões)",
  comments: "comentário(s)",
  membership_notifications: "notificação(ões)",
  sessions: "sessão(ões)",
  otp_challenges: "validação(ões) OTP",
  otp_deliveries: "entrega(s) OTP",
  facial_searches: "busca(s) facial(is) transitória(s)",
  orders: "pedido(s)",
  order_items: "item(ns) comprado(s)",
  payment_communications: "comunicação(ões) de pagamento",
  payment_notifications: "notificação(ões) de pagamento",
  commercial_media: "mídia(s) do histórico comercial",
  payment_deliveries: "entrega(s) de pagamento",
};

export async function clientJsonRequest(path: string, init?: RequestInit) {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail?.message ?? "Não foi possível concluir a operação.",
    );
  }
  return response.status === 204 ? null : response.json();
}

export function ClientCreateForm({
  onCreated,
  submitLabel = "Cadastrar cliente",
}: {
  onCreated: (client: ClientDirectoryItem) => void | Promise<void>;
  submitLabel?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("full_name") ?? "").trim();
    const phone = String(form.get("phone_e164") ?? "").trim();
    setBusy(true);
    setError("");
    try {
      const created = (await clientJsonRequest("/api/admin/clients", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ full_name: name, phone_e164: phone }),
      })) as { id: string };
      await onCreated({ id: created.id, name, phone });
      formElement.reset();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Não foi possível cadastrar a cliente.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="gallery-settings-form" onSubmit={submit}>
      <label>
        Nome completo
        <input name="full_name" required minLength={3} />
      </label>
      <label>
        Número do WhatsApp
        <input name="phone_e164" required placeholder="+55 11 99999-9999" />
      </label>
      {error ? (
        <p className="form-message form-message--error" role="alert">
          {error}
        </p>
      ) : null}
      <MarkinaButton disabled={busy}>{busy ? "Cadastrando…" : submitLabel}</MarkinaButton>
    </form>
  );
}

export function ClientEditorDialog({
  client,
  onClose,
  onDeleted,
  onUpdated,
}: {
  client: ClientDirectoryItem;
  onClose: () => void;
  onDeleted: (clientId: string) => void;
  onUpdated: (client: ClientDirectoryItem) => void;
}) {
  const [name, setName] = useState(client.name);
  const [phone, setPhone] = useState(client.phone);
  const [challengeId, setChallengeId] = useState("");
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [inventory, setInventory] = useState<ClientDeletionInventory | null>(null);
  const deletionKey = useRef(crypto.randomUUID());

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const phoneChanged = phone.trim() !== client.phone;
      if (phoneChanged && !challengeId) {
        const challenge = (await clientJsonRequest("/api/auth/client/challenge", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ full_name: name, phone }),
        })) as { challenge_id: string };
        setChallengeId(challenge.challenge_id);
        return;
      }
      if (phoneChanged) {
        await clientJsonRequest(`/api/admin/clients/${client.id}/phone`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ phone_e164: phone, challenge_id: challengeId, code: otp }),
        });
      }
      if (name.trim() !== client.name) {
        await clientJsonRequest(`/api/admin/clients/${client.id}`, {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ full_name: name }),
        });
      }
      onUpdated({ ...client, name: name.trim(), phone: phone.trim() });
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Não foi possível atualizar a cliente.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function inspectDeletion() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      setInventory(
        (await clientJsonRequest(
          `/api/admin/clients/${client.id}/deletion-inventory`,
        )) as ClientDeletionInventory,
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Não foi possível verificar a exclusão.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirmDeletion() {
    if (!inventory?.can_delete || busy) return;
    setBusy(true);
    setError("");
    try {
      await clientJsonRequest(`/api/admin/clients/${client.id}`, {
        method: "DELETE",
        headers: { "Idempotency-Key": deletionKey.current },
      });
      onDeleted(client.id);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Não foi possível excluir a cliente.",
      );
    } finally {
      setBusy(false);
    }
  }

  const protectedEntries = Object.entries(inventory?.commercial_protected ?? {}).filter(
    ([, quantity]) => quantity > 0,
  );
  const operationalEntries = Object.entries(inventory?.operational_removable ?? {}).filter(
    ([, quantity]) => quantity > 0,
  );

  return (
    <div className="mk-dialog-backdrop" role="presentation">
      <section
        aria-labelledby="edit-client-title"
        aria-modal="true"
        className="mk-dialog client-edit-dialog"
        role="dialog"
      >
        <p className="eyebrow">Cadastro da cliente</p>
        <h2 id="edit-client-title">Editar {client.name}</h2>
        <p>
          Atualize a mesma identidade para preservar galerias e histórico. A troca de WhatsApp
          exige o código enviado ao novo número.
        </p>
        <form className="gallery-settings-form" onSubmit={save}>
          <label>
            Nome completo
            <input
              value={name}
              required
              minLength={3}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            Número do WhatsApp
            <input
              value={phone}
              required
              placeholder="+55 11 99999-9999"
              onChange={(event) => {
                setPhone(event.target.value);
                setChallengeId("");
                setOtp("");
              }}
            />
          </label>
          {challengeId ? (
            <label>
              Código enviado ao novo WhatsApp
              <input
                value={otp}
                inputMode="numeric"
                pattern="[0-9]{6}"
                minLength={6}
                maxLength={6}
                required
                onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))}
              />
            </label>
          ) : null}
          {error ? (
            <p className="form-message form-message--error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="mk-dialog__actions">
            <MarkinaButton type="button" variant="secondary" disabled={busy} onClick={onClose}>
              Cancelar
            </MarkinaButton>
            <MarkinaButton disabled={busy}>
              {busy
                ? "Salvando…"
                : phone.trim() !== client.phone && !challengeId
                  ? "Enviar código"
                  : "Salvar cadastro"}
            </MarkinaButton>
          </div>
        </form>
        <div className="client-delete-zone">
          <strong>Excluir cadastro criado por engano</strong>
          <p>
            Vínculos e interações sem compra serão removidos. Pedidos, pagamentos e entregas
            comerciais sempre impedem a exclusão.
          </p>
          {!inventory ? (
            <MarkinaButton type="button" variant="quiet" disabled={busy} onClick={inspectDeletion}>
              Verificar exclusão
            </MarkinaButton>
          ) : inventory.can_delete ? (
            <div className="client-delete-confirmation">
              <strong>Consequências desta exclusão</strong>
              <ul>
                {operationalEntries.map(([key, quantity]) => (
                  <li key={key}>
                    {quantity} {inventoryLabels[key] ?? key}
                  </li>
                ))}
              </ul>
              <p>
                Galerias públicas, fotos originais, outras clientes e privadas compartilhadas
                serão preservadas.
              </p>
              <MarkinaButton
                type="button"
                className="mk-button--danger"
                disabled={busy}
                onClick={confirmDeletion}
              >
                {busy ? "Excluindo…" : "Excluir cadastro definitivamente"}
              </MarkinaButton>
            </div>
          ) : (
            <div className="client-delete-blocked" role="status">
              <strong>Exclusão bloqueada pelo histórico comercial</strong>
              <ul>
                {protectedEntries.map(([key, quantity]) => (
                  <li key={key}>
                    {quantity} {inventoryLabels[key] ?? key}
                  </li>
                ))}
              </ul>
              <p>Edite o telefone ou administre os vínculos sem apagar o histórico.</p>
              <Link className="mk-button mk-button--secondary" href="/admin/galleries">
                Administrar vínculos nas galerias
              </Link>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
