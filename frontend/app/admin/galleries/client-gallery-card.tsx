import Link from "next/link";
import type { ReactNode } from "react";

import { StatusBadge } from "../../ui-kit";

export type ClientGalleryRow = {
  client_id: string;
  name: string;
  phone: string;
  phone_verified?: boolean;
  registration_status: string | null;
  membership_status?: "active" | "blocked" | "unlinked" | null;
  derived_gallery_id: string | null;
  available_count: number;
  selected_count: number;
  purchased_count: number;
  gallery_status: "pending_registration" | "no_selection" | "blocked" | "expired" | "active";
  commercial_status?: "pending_review" | "awaiting_payment" | "paid" | "overdue" | "cancelled" | "no_order";
};

const galleryStatus = {
  pending_registration: { label: "Aguardando primeiro acesso", tone: "warning" },
  no_selection: { label: "Sem seleção", tone: "warning" },
  blocked: { label: "Galeria bloqueada", tone: "dark" },
  expired: { label: "Galeria expirada", tone: "warning" },
  active: { label: "Galeria ativa", tone: "success" },
} as const;

const commercialStatus = {
  pending_review: { label: "Pagamento comunicado", tone: "warning" },
  awaiting_payment: { label: "Aguardando pagamento", tone: "neutral" },
  paid: { label: "Pago", tone: "success" },
  overdue: { label: "Prazo expirado", tone: "danger" },
  cancelled: { label: "Pedido cancelado", tone: "dark" },
  no_order: { label: "Sem pedido", tone: "neutral" },
} as const;

export function ClientGalleryCard({ person, actions }: { person: ClientGalleryRow; actions?: ReactNode }) {
  const access = galleryStatus[person.gallery_status];
  const commercial = commercialStatus[person.commercial_status ?? "no_order"];
  return <article aria-label={`Cliente ${person.name}`} className={`gallery-linked-client gallery-linked-client--${person.gallery_status}`}>
    <header>
      <div>
        {person.derived_gallery_id ? <Link href={`/admin/galleries/${person.derived_gallery_id}`}>{person.name}</Link> : <strong>{person.name}</strong>}
        <small>{person.phone}</small>
      </div>
      <span className="gallery-client-badges" aria-label="Estados da cliente">
        <StatusBadge tone={access.tone}>{access.label}</StatusBadge>
        <StatusBadge tone={commercial.tone}>{commercial.label}</StatusBadge>
      </span>
    </header>
    <dl className="gallery-client-counts">
      <div><dt>Disponíveis</dt><dd>{person.available_count}</dd></div>
      <div><dt>Selecionadas</dt><dd>{person.selected_count}</dd></div>
      <div><dt>Compradas</dt><dd>{person.purchased_count}</dd></div>
    </dl>
    {person.gallery_status === "pending_registration" ? <p className="gallery-client-pending">O vínculo já existe. No primeiro acesso pelo link, a cliente ainda precisa validar este WhatsApp com o código OTP.</p> : null}
    {person.derived_gallery_id ? <Link className="gallery-client-open" href={`/admin/galleries/${person.derived_gallery_id}`}>Abrir galeria privada</Link> : <p className="gallery-client-pending">A galeria privada será criada quando houver fotos disponíveis ou uma primeira seleção.</p>}
    {actions ? <div className="gallery-client-card-actions">{actions}</div> : null}
  </article>;
}
