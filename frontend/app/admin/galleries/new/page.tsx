"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { MarkinaButton, MarkinaLink, PageHeading } from "../../../ui-kit";
import { OverviewIcon } from "../../overview-icon";
import styles from "./new-gallery.module.css";

export default function NewGalleryPage() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const request = useRef<AbortController | null>(null);

  useEffect(() => () => request.current?.abort(), []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (request.current) return;

    const controller = new AbortController();
    const form = new FormData(event.currentTarget);
    request.current = controller;
    setSaving(true);
    setMessage("");
    let redirecting = false;

    try {
      const response = await fetch("/api/admin/parent-galleries", {
        method: "POST",
        credentials: "same-origin",
        signal: controller.signal,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: form.get("name"),
          event_name: form.get("event_name") || null,
          description: form.get("description") || null,
        }),
      });
      if (controller.signal.aborted) return;
      if (!response.ok && response.status < 500) {
        setMessage("Não foi possível criar a galeria. Revise os dados e tente novamente.");
        return;
      }
      if (!response.ok) throw new Error();

      const data = await response.json() as { id?: unknown } | null;
      if (controller.signal.aborted) return;
      if (typeof data?.id !== "string" || !data.id) throw new Error();
      router.push(`/admin/galleries/sources/${encodeURIComponent(data.id)}/edit/ajustes`);
      redirecting = true;
    } catch {
      if (!controller.signal.aborted) {
        setMessage("Não foi possível confirmar a criação. Confira a lista de galerias antes de reenviar.");
      }
    } finally {
      if (!controller.signal.aborted && !redirecting) {
        request.current = null;
        setSaving(false);
      }
    }
  }

  return (
    <div className={styles.page}>
      <Link className={styles.back} href="/admin/galleries"><span aria-hidden="true">←</span> Voltar para galerias</Link>
      <PageHeading
        eyebrow="Nova galeria"
        title="Comece pelos dados essenciais."
        detail="Crie a galeria com os dados iniciais. Você poderá configurar os ajustes e adicionar fotos nas próximas etapas."
      />
      <form aria-label="Dados da nova galeria" aria-busy={saving} className={styles.form} onSubmit={submit}>
        <div className={styles.field}>
          <div className={styles.fieldHeading}>
            <label htmlFor="new-gallery-name">Título da galeria</label>
            <span className={styles.required} aria-hidden="true">Obrigatório</span>
          </div>
          <p id="new-gallery-name-detail">Nome que identifica a galeria no acervo e para as suas clientes.</p>
          <input id="new-gallery-name" aria-describedby="new-gallery-name-detail" name="name" required maxLength={200} autoFocus />
        </div>
        <div className={styles.field}>
          <div className={styles.fieldHeading}>
            <label htmlFor="new-gallery-event">Nome do evento</label>
            <span>Opcional</span>
          </div>
          <p id="new-gallery-event-detail">Nome do ensaio, da celebração ou do evento.</p>
          <input id="new-gallery-event" aria-describedby="new-gallery-event-detail" name="event_name" maxLength={200} />
        </div>
        <div className={styles.field}>
          <div className={styles.fieldHeading}>
            <label htmlFor="new-gallery-description">Descrição administrativa</label>
            <span>Opcional</span>
          </div>
          <p id="new-gallery-description-detail">Use para anotar o contexto ou detalhes internos do trabalho.</p>
          <textarea id="new-gallery-description" aria-describedby="new-gallery-description-detail" name="description" maxLength={5000} rows={4} />
        </div>
        {message ? <p className="form-message form-message--error" role="alert">{message}</p> : null}
        <div className={styles.actions}>
          <MarkinaLink href="/admin/galleries" variant="secondary">Cancelar</MarkinaLink>
          <MarkinaButton type="submit" disabled={saving}>
            <OverviewIcon name="add" /> {saving ? "Criando…" : "Criar e continuar"}
          </MarkinaButton>
        </div>
      </form>
    </div>
  );
}
