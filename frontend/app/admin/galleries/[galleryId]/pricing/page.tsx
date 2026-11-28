"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { MarkinaLink, PageHeading, StatusBadge, SystemState } from "../../../../ui-kit";
import { OverviewIcon } from "../../../overview-icon";
import catalogStyles from "../../../catalog.module.css";
import styles from "../private-gallery.module.css";
import { formatBrazilianCurrency, type PriceTier } from "../../pricing-rules";

type InheritedPricing = {
  inherited_from_parent_gallery_id: string;
  editable: false;
  pricing_mode?: "fixed" | "progressive" | "legacy_volume";
  fixed_unit_price_cents?: number | null;
  pricing_review_required?: boolean;
  pricing_snapshot?: { mode?: string; preset_name?: string; preset_version?: number; tiers?: PriceTier[] } | null;
};

export default function GalleryPricingPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [result, setResult] = useState<{ galleryId: string; pricing: InheritedPricing | null } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/admin/derived-galleries/${galleryId}/pricing`, { credentials: "same-origin", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("pricing request failed");
        const pricing = await response.json() as InheritedPricing;
        if (!controller.signal.aborted) setResult({ galleryId, pricing });
      })
      .catch(() => { if (!controller.signal.aborted) setResult({ galleryId, pricing: null }); });
    return () => controller.abort();
  }, [galleryId]);

  const current = result?.galleryId === galleryId ? result : null;
  const pricing = current?.pricing;
  const fixedPrice = pricing?.pricing_mode === "fixed" ? pricing.fixed_unit_price_cents : null;
  const snapshot = pricing?.pricing_mode === "progressive" && pricing.pricing_snapshot?.mode === "progressive"
    ? pricing.pricing_snapshot
    : null;

  return <div className={catalogStyles.catalog}>
    <Link className={styles.back} href={`/admin/galleries/${galleryId}`}><span aria-hidden="true">←</span> Voltar para a galeria privada</Link>
    <PageHeading eyebrow="Configuração comercial herdada" title="Preços pertencem à Galeria pública; PIX vale para sua conta" detail="A galeria privada usa a configuração da origem. Os pedidos anteriores mantêm os valores registrados na compra." />
    {!current ? <SystemState tone="loading" title="Localizando a configuração da Galeria pública…" detail="Consultando os parâmetros herdados." /> : !pricing ? (
      <SystemState tone="error" title="Configuração indisponível" detail="Não foi possível localizar a configuração comercial herdada." />
    ) : <>
      <section className={styles.inherited} aria-labelledby="inherited-pricing-title">
        <div className={styles.pricingHeading}>
          <span className={styles.pricingIcon}><OverviewIcon name="payments" /></span>
          <h2 id="inherited-pricing-title">Condições herdadas</h2>
          <StatusBadge>Somente leitura</StatusBadge>
        </div>
        {pricing.pricing_review_required || pricing.pricing_mode === "legacy_volume" ? <p>Revise a precificação legada na etapa Vendas da Galeria pública.</p>
          : fixedPrice != null ? <dl className={styles.priceList}><div><dt>Preço fixo por foto</dt><dd>{formatBrazilianCurrency(fixedPrice)}</dd></div></dl>
            : snapshot?.tiers?.length ? <>
              <h3>{snapshot.preset_name || "Tabela progressiva"}{snapshot.preset_version != null ? ` · versão ${snapshot.preset_version}` : ""}</h3>
              <dl className={styles.priceList}>{snapshot.tiers.map((tier) => <div key={tier.minimum_quantity}><dt>{tier.minimum_quantity}–{tier.maximum_quantity ?? "∞"} fotos</dt><dd>{formatBrazilianCurrency(tier.unit_price_cents)} cada</dd></div>)}</dl>
            </> : <p>Consulte as condições atuais na etapa Vendas da Galeria pública.</p>}
        <div className={styles.pricingActions}>
          <MarkinaLink href={`/admin/galleries/sources/${pricing.inherited_from_parent_gallery_id}/edit/vendas`}>Abrir etapa Vendas da Galeria pública</MarkinaLink>
          <MarkinaLink href="/admin/settings#pix" variant="secondary">Configurar PIX da sua conta</MarkinaLink>
        </div>
      </section>
    </>}
  </div>;
}
