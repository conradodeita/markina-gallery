"use client";

import { useEffect, useState } from "react";
import { SurfaceCard } from "../../ui-kit";

type Acceptance = {
  id: string;
  version: string;
  text: string;
  sha256: string;
  provider_identity: string;
  photographer_identity: string;
  accepted_at: string;
  environment: string;
};

export function PhotographerTermsHistory({ tenantId }: { tenantId: string }) {
  const [items, setItems] = useState<Acceptance[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`/api/admin/platform/terms/acceptances/${encodeURIComponent(tenantId)}`, {
      credentials: "same-origin", cache: "no-store",
    }).then(async (response) => {
      if (!response.ok) throw new Error("Falha ao consultar protocolos.");
      const result = await response.json() as { items: Acceptance[] };
      if (active) setItems(result.items);
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [tenantId]);

  return <SurfaceCard>
    <h2>Histórico de aceite dos Termos</h2>
    {error ? <p role="alert">Não foi possível consultar os protocolos de aceite.</p> : null}
    {items === null && !error ? <p role="status">Consultando protocolos…</p> : null}
    {items?.length === 0 ? <p>Nenhum aceite registrado para esta conta.</p> : null}
    {items?.map((item) => <details key={item.id}>
      <summary>{item.version} · {new Date(item.accepted_at).toLocaleString("pt-BR", { timeZone: "UTC" })} UTC</summary>
      <p>Provedor: {item.provider_identity}</p>
      <p>Fotógrafo: {item.photographer_identity}</p>
      <p>SHA-256: {item.sha256}</p>
      <p>Ambiente: {item.environment}</p>
      <pre style={{ whiteSpace: "pre-wrap" }}>{item.text}</pre>
    </details>)}
  </SurfaceCard>;
}
