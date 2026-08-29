"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

type Tier = {
  minimum_quantity: number;
  maximum_quantity: number | null;
  unit_price_cents: number;
};
type Pix = {
  copy_paste: string | null;
  qr_code_payload: string | null;
  instructions: string | null;
};
type Pricing = { tiers: Tier[]; pix: Pix };

const initialPricing: Pricing = {
  tiers: [{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 0 }],
  pix: { copy_paste: null, qr_code_payload: null, instructions: null },
};

function hasDownwardJump(tiers: Tier[]) {
  return tiers.some((tier, index) => {
    const next = tiers[index + 1];
    return next !== undefined && tier.maximum_quantity !== null
      && next.minimum_quantity * next.unit_price_cents < tier.maximum_quantity * tier.unit_price_cents;
  });
}

export default function GalleryPricingPage() {
  const { galleryId } = useParams<{ galleryId: string }>();
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [message, setMessage] = useState("");
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    fetch(`/api/admin/derived-galleries/${galleryId}/pricing`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error("pricing request failed");
        const result = await response.json() as Pricing;
        setPricing({ ...result, tiers: result.tiers.length ? result.tiers : initialPricing.tiers });
      })
      .catch(() => setLoadError(true));
  }, [galleryId]);

  const warning = useMemo(() => pricing ? hasDownwardJump(pricing.tiers) : false, [pricing]);

  function updateTier(index: number, patch: Partial<Tier>) {
    setPricing((current) => current && {
      ...current,
      tiers: current.tiers.map((tier, tierIndex) => tierIndex === index ? { ...tier, ...patch } : tier),
    });
  }

  function addTier() {
    setPricing((current) => {
      if (!current) return current;
      const last = current.tiers.at(-1)!;
      const end = last.maximum_quantity ?? last.minimum_quantity;
      return {
        ...current,
        tiers: [...current.tiers.slice(0, -1), { ...last, maximum_quantity: end }, {
          minimum_quantity: end + 1,
          maximum_quantity: null,
          unit_price_cents: last.unit_price_cents,
        }],
      };
    });
  }

  function removeTier(index: number) {
    setPricing((current) => {
      if (!current || current.tiers.length === 1) return current;
      const tiers = current.tiers.filter((_, tierIndex) => tierIndex !== index);
      return {
        ...current,
        tiers: tiers.map((tier, tierIndex) => ({
          ...tier,
          minimum_quantity: tierIndex === 0 ? 1 : (tiers[tierIndex - 1].maximum_quantity ?? tier.minimum_quantity - 1) + 1,
        })),
      };
    });
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pricing) return;
    if (hasDownwardJump(pricing.tiers) && !window.confirm(
      "Uma faixa reduz o valor total ao aumentar a quantidade. Deseja salvar mesmo assim?",
    )) return;
    const response = await fetch(`/api/admin/derived-galleries/${galleryId}/pricing`, {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pricing),
    });
    if (!response.ok) {
      setMessage("Revise as faixas: elas devem começar em uma foto, ser contíguas e usar valores válidos.");
      return;
    }
    setPricing(await response.json());
    setMessage("Preço e instruções PIX salvos. Nenhum pagamento foi confirmado.");
  }

  if (loadError) return <main className="admin-shell"><h1>Configuração indisponível</h1><p className="notice" role="alert">Não foi possível carregar as regras comerciais. Nenhuma alteração foi salva.</p><Link href={`/admin/galleries/${galleryId}`}>Voltar para a galeria</Link></main>;
  if (!pricing) return <main className="admin-shell"><p role="status">Carregando regras comerciais…</p></main>;

  return <main className="admin-shell">
    <Link href={`/admin/galleries/${galleryId}`}>← Galeria</Link>
    <p className="eyebrow">Vendas · configuração por galeria</p>
    <h1>Preço e PIX manual</h1>
    <p className="intro">Os valores são aplicados no servidor e congelados no pedido. Esta tela não confirma pagamentos.</p>
    <form className="auth-form" onSubmit={save}>
      <fieldset>
        <legend>Faixas de preço</legend>
        {pricing.tiers.map((tier, index) => <div className="pricing-tier" key={`${tier.minimum_quantity}-${index}`}>
          <label>De<input value={tier.minimum_quantity} readOnly aria-label={`Início da faixa ${index + 1}`} /></label>
          <label>Até<input type="number" min={tier.minimum_quantity} value={tier.maximum_quantity ?? ""} onChange={(event) => updateTier(index, { maximum_quantity: event.target.value ? Number(event.target.value) : null })} placeholder="sem limite" aria-label={`Fim da faixa ${index + 1}`} /></label>
          <label>R$ por foto<input type="number" min="0" step="0.01" value={(tier.unit_price_cents / 100).toFixed(2)} onChange={(event) => updateTier(index, { unit_price_cents: Math.round(Number(event.target.value.replace(",", ".")) * 100) || 0 })} aria-label={`Preço por foto da faixa ${index + 1}`} required /></label>
          {pricing.tiers.length > 1 && <button type="button" className="link-button" onClick={() => removeTier(index)}>Remover faixa</button>}
        </div>)}
        <button type="button" className="secondary" onClick={addTier}>Adicionar faixa</button>
      </fieldset>
      {warning && <p className="notice" role="alert">A próxima faixa reduz o total ao aumentar a quantidade. Confirme essa decisão antes de salvar.</p>}
      <fieldset>
        <legend>Instruções PIX</legend>
        <label>Copia e cola<textarea value={pricing.pix.copy_paste ?? ""} onChange={(event) => setPricing({ ...pricing, pix: { ...pricing.pix, copy_paste: event.target.value || null } })} maxLength={4000} /></label>
        <label>Payload do QR Code<textarea value={pricing.pix.qr_code_payload ?? ""} onChange={(event) => setPricing({ ...pricing, pix: { ...pricing.pix, qr_code_payload: event.target.value || null } })} maxLength={8000} /></label>
        <label>Orientação à cliente<input value={pricing.pix.instructions ?? ""} onChange={(event) => setPricing({ ...pricing, pix: { ...pricing.pix, instructions: event.target.value || null } })} maxLength={500} /></label>
      </fieldset>
      <button className="primary">Salvar regras comerciais</button>
    </form>
    {message && <p className="form-message" role="status">{message}</p>}
  </main>;
}
