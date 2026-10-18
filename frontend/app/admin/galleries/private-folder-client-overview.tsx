"use client";

import { useEffect, useState } from "react";

import { MarkinaButton, MarkinaLink, StatusBadge, SystemState } from "../../ui-kit";

type Person = { id: string; name: string };
type PrivateFolderGallery = {
  id: string;
  name: string;
  owner: Person;
  active_members: Person[];
  folders: { id: string; name: string; status: string; photo_count: number }[];
};

export function PrivateFolderClientOverview({ sourceId, refreshToken = 0 }: { sourceId: string; refreshToken?: number }) {
  const [state, setState] = useState<{ loading: boolean; error: boolean; galleries: PrivateFolderGallery[] }>({ loading: true, error: false, galleries: [] });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    queueMicrotask(() => { if (active) setState({ loading: true, error: false, galleries: [] }); });
    void fetch(`/api/admin/parent-galleries/${sourceId}/private-folders`, {
      credentials: "same-origin", cache: "no-store", signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) throw new Error("Consulta indisponível");
      return response.json() as Promise<{ galleries: PrivateFolderGallery[] }>;
    }).then((result) => {
      if (active) setState({ loading: false, error: false, galleries: result.galleries ?? [] });
    }).catch(() => {
      if (active) setState({ loading: false, error: true, galleries: [] });
    });
    return () => { active = false; controller.abort(); };
  }, [sourceId, refreshToken, retry]);

  return <section className="admin-card" aria-label="Pastas de galerias privadas">
    <header className="section-heading"><div><p className="eyebrow">Acervo exclusivo das clientes</p><h3>Pastas de galerias privadas</h3></div></header>
    <p className="gallery-scope-note">Confira a responsável de cada pasta. Para carregar fotos exclusivas, abra a galeria privada correspondente.</p>
    {state.loading ? <SystemState title="Carregando pastas privadas" detail="Consultando responsáveis e membros ativos." tone="loading" />
      : state.error ? <><SystemState title="Não foi possível consultar as pastas privadas" detail="Tente novamente para identificar as responsáveis." tone="error" /><MarkinaButton type="button" variant="secondary" onClick={() => setRetry((value) => value + 1)}>Tentar novamente</MarkinaButton></>
        : !state.galleries.length ? <SystemState title="Nenhuma pasta privada nesta galeria" detail="As pastas privadas aparecerão aqui com a identificação das responsáveis." />
          : <div className="private-access-list">{state.galleries.map((gallery) => <article className="private-access-card" key={gallery.id} aria-label={`Galeria privada ${gallery.name}`}>
            <header><div><h4>{gallery.name}</h4><strong>Responsável principal: {gallery.owner.name}</strong></div><StatusBadge>Privada</StatusBadge></header>
            {gallery.active_members.length ? <div><p>{gallery.active_members.some((member) => member.id !== gallery.owner.id) ? "Acesso compartilhado — membros ativos:" : "Membro ativo:"}</p><ul>{gallery.active_members.map((member) => <li key={member.id}>{member.name}</li>)}</ul></div> : <p>Nenhum membro ativo cadastrado.</p>}
            <ul aria-label={`Pastas de ${gallery.owner.name}`}>{gallery.folders.map((folder) => <li key={folder.id}><strong>{folder.name}</strong> · {folder.photo_count} foto(s) · <StatusBadge tone={folder.status === "released" ? "success" : "warning"}>{folder.status === "released" ? "Disponível" : "Em preparação"}</StatusBadge></li>)}</ul>
            <div className="gallery-access-actions"><MarkinaLink href={`/admin/galleries/${gallery.id}`} variant="secondary">Abrir galeria privada de {gallery.owner.name}</MarkinaLink></div>
          </article>)}</div>}
  </section>;
}
