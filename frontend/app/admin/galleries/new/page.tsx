"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { MarkinaButton } from "../../../ui-kit";

export default function NewGalleryPage() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/admin/parent-galleries", {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: form.get("name"),
        event_name: form.get("event_name") || null,
        description: form.get("description") || null,
      }),
    });
    if (!response.ok) {
      setSaving(false);
      setMessage("Não foi possível criar a galeria. Revise os dados e tente novamente.");
      return;
    }
    const data = await response.json();
    router.push(`/admin/galleries/sources/${data.id}/edit/ajustes`);
  }

  return (
    <main className="admin-shell gallery-create-shell">
      <Link href="/admin/galleries">← Voltar para galerias</Link>
      <p className="eyebrow">Nova galeria</p>
      <h1>Comece pelos dados essenciais.</h1>
      <p className="intro">
        Depois de salvar, você seguirá por Ajustes, Vendas, Detalhes, Imagens e Clientes.
        Pastas e fotos sempre nascerão dentro desta galeria.
      </p>
      <form className="gallery-editor-panel gallery-settings-form" onSubmit={submit}>
        <label>
          Título da galeria
          <input name="name" required maxLength={200} autoFocus />
        </label>
        <label>
          Nome do evento
          <input name="event_name" maxLength={200} />
        </label>
        <label>
          Descrição administrativa
          <textarea name="description" maxLength={5000} rows={4} />
        </label>
        {message ? <p className="notice" role="alert">{message}</p> : null}
        <div className="gallery-editor-actions">
          <Link className="mk-button mk-button--secondary" href="/admin/galleries">Cancelar</Link>
          <MarkinaButton disabled={saving}>{saving ? "Criando…" : "Criar e continuar"}</MarkinaButton>
        </div>
      </form>
    </main>
  );
}
