"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type InheritedPricing = {
  inherited_from_parent_gallery_id: string;
  editable: false;
};

export default function GalleryPricingPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [pricing, setPricing] = useState<InheritedPricing | null>(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    fetch(`/api/admin/derived-galleries/${galleryId}/pricing`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error("pricing request failed");
        setPricing(await response.json() as InheritedPricing);
      })
      .catch(() => setLoadError(true));
  }, [galleryId]);

  if (loadError) return <main className="admin-shell"><h1>Configuração indisponível</h1><p className="notice" role="alert">Não foi possível localizar a configuração comercial herdada.</p><Link href={`/admin/galleries/${galleryId}`}>Voltar para a galeria privada</Link></main>;
  if (!pricing) return <main className="admin-shell"><p role="status">Localizando a configuração da Galeria pública…</p></main>;

  return <main className="admin-shell">
    <Link href={`/admin/galleries/${galleryId}`}>← Galeria privada</Link>
    <p className="eyebrow">Vendas · configuração herdada</p>
    <h1>Preço e PIX pertencem à Galeria pública</h1>
    <p className="intro">Esta galeria privada reutiliza faixas, PIX, mensagem, prazo e interações da origem. Pedidos já criados mantêm o snapshot comercial gravado no momento da compra.</p>
    <Link className="mk-button mk-button--primary" href={`/admin/galleries/sources/${pricing.inherited_from_parent_gallery_id}/edit/vendas`}>Abrir etapa Vendas da Galeria pública</Link>
  </main>;
}
