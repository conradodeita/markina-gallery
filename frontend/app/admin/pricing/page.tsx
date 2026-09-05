"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { MarkinaButton, PageHeading, StatusBadge, SurfaceCard, SystemState } from "../../ui-kit";
import {
  formatBrazilianCurrency,
  maskBrazilianCurrencyInput,
  parseBrazilianCurrency,
  type PriceTier,
} from "../galleries/pricing-rules";

type Preset = {
  id: string;
  code: string;
  name: string;
  label: string;
  version: number;
  active: boolean;
  tiers: PriceTier[];
};

const emptyTier: PriceTier = { minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 0 };

export default function PricingPresetsPage() {
  const [presets, setPresets] = useState<Preset[] | null>(null);
  const [editing, setEditing] = useState<Preset | null>(null);
  const [tiers, setTiers] = useState<PriceTier[]>([emptyTier]);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const response = await fetch("/api/admin/pricing-presets?include_inactive=true", {
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error();
    setPresets((await response.json()).presets);
  }, []);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      load().catch(() => {
        if (active) setMessage("Não foi possível carregar as tabelas de preço.");
      });
    });
    return () => { active = false; };
  }, [load]);

  function startEdit(preset: Preset) {
    setEditing(preset);
    setTiers(preset.tiers.map((tier) => ({ ...tier })));
    setMessage("");
  }

  function resetForm() {
    setEditing(null);
    setTiers([{ ...emptyTier }]);
  }

  function addTier() {
    setTiers((current) => {
      const last = current.at(-1)!;
      const maximum = last.maximum_quantity ?? last.minimum_quantity;
      return [
        ...current.slice(0, -1),
        { ...last, maximum_quantity: maximum },
        {
          minimum_quantity: maximum + 1,
          maximum_quantity: null,
          unit_price_cents: last.unit_price_cents,
        },
      ];
    });
  }

  function updateTierPrice(index: number, value: string) {
    const formatted = maskBrazilianCurrencyInput(value);
    const cents = parseBrazilianCurrency(formatted) ?? 0;
    setTiers((current) => current.map((tier, tierIndex) => (
      tierIndex === index ? { ...tier, unit_price_cents: cents } : tier
    )));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const parsedTiers = tiers.map((tier, index) => {
      const cents = parseBrazilianCurrency(String(data.get(`price_${index}`) ?? ""));
      return cents === null ? null : { ...tier, unit_price_cents: cents };
    });
    if (parsedTiers.some((tier) => tier === null)) {
      setMessage("Informe todos os valores como moeda brasileira, por exemplo R$ 7,00.");
      return;
    }
    setSaving(true);
    setMessage("");
    const response = await fetch(
      editing ? `/api/admin/pricing-presets/${editing.id}` : "/api/admin/pricing-presets",
      {
        method: editing ? "PUT" : "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: data.get("code"),
          name: data.get("name"),
          tiers: parsedTiers,
        }),
      },
    );
    if (response.ok) {
      await load();
      resetForm();
      form.reset();
      setMessage(editing ? "Tabela atualizada em uma nova versão." : "Tabela criada.");
    } else {
      const body = await response.json().catch(() => ({}));
      setMessage(body.detail ?? "Não foi possível salvar a tabela.");
    }
    setSaving(false);
  }

  async function setActive(preset: Preset, active: boolean) {
    if (!active && !window.confirm(`Desativar ${preset.label}? Galerias existentes manterão seus valores.`)) return;
    const response = await fetch(`/api/admin/pricing-presets/${preset.id}${active ? "/activate" : ""}`, {
      method: active ? "POST" : "DELETE",
      credentials: "same-origin",
    });
    const action = active ? "ativar" : "desativar";
    setMessage(response.ok
      ? active
        ? "Tabela reativada e disponível para novas galerias."
        : "Tabela desativada sem alterar galerias existentes."
      : `Não foi possível ${action} a tabela.`);
    if (response.ok) await load();
  }

  return (
    <div className="admin-shell pricing-presets-page">
      <PageHeading
        eyebrow="Configuração comercial global"
        title="Tabelas de preço progressivo"
        detail="Cadastre uma vez e selecione a tabela desejada na etapa Vendas de cada Galeria pública."
      />
      {message ? <p className="form-message" role="status">{message}</p> : null}
      <div className="pricing-presets-layout">
        <SurfaceCard>
          <h2>{editing ? `Editar ${editing.label}` : "Nova tabela"}</h2>
          <form className="pricing-preset-form" onSubmit={submit}>
            <div className="pricing-preset-identity">
              <label>Código<input defaultValue={editing?.code ?? ""} key={`code-${editing?.id ?? "new"}`} name="code" placeholder="01" required /></label>
              <label>Nome<input defaultValue={editing?.name ?? ""} key={`name-${editing?.id ?? "new"}`} name="name" placeholder="Tabela escolar" required /></label>
            </div>
            <div className="pricing-tier-editor">
              <div><strong>Faixas progressivas</strong><small>Cada intervalo cobra somente as fotos contidas nele.</small></div>
              {tiers.map((tier, index) => (
                <div className="pricing-tier-row" key={`${editing?.id ?? "new"}-${index}`}>
                  <span>{tier.minimum_quantity}–{tier.maximum_quantity ?? "∞"} fotos</span>
                  <label>Valor unitário<input value={formatBrazilianCurrency(tier.unit_price_cents)} name={`price_${index}`} inputMode="numeric" onChange={(event) => updateTierPrice(index, event.target.value)} required /></label>
                  {index < tiers.length - 1 ? <label>Até<input min={tier.minimum_quantity} type="number" value={tier.maximum_quantity ?? tier.minimum_quantity} onChange={(event) => setTiers((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, maximum_quantity: Number(event.target.value) } : itemIndex === index + 1 ? { ...item, minimum_quantity: Number(event.target.value) + 1 } : item))} /></label> : <small>Última faixa sem limite</small>}
                </div>
              ))}
              <MarkinaButton type="button" variant="secondary" onClick={addTier}>Adicionar faixa</MarkinaButton>
            </div>
            <div className="pricing-form-actions">
              {editing ? <MarkinaButton type="button" variant="secondary" onClick={resetForm}>Cancelar edição</MarkinaButton> : null}
              <MarkinaButton disabled={saving} type="submit">{saving ? "Salvando…" : "Salvar tabela"}</MarkinaButton>
            </div>
          </form>
        </SurfaceCard>
        <section className="pricing-preset-list" aria-label="Tabelas cadastradas">
          {presets === null && !message ? <SystemState tone="loading" title="Carregando tabelas" detail="Consultando versões e faixas." /> : null}
          {presets?.length === 0 ? <SystemState title="Nenhuma tabela cadastrada" detail="Crie a primeira tabela progressiva ao lado." /> : null}
          {presets?.map((preset) => (
            <SurfaceCard className="pricing-preset-card" key={preset.id}>
              <header><div><strong>{preset.label}</strong><small>Versão {preset.version}</small></div><StatusBadge tone={preset.active ? "success" : "neutral"}>{preset.active ? "Ativa" : "Desativada"}</StatusBadge></header>
              <dl>{preset.tiers.map((tier) => <div key={tier.minimum_quantity}><dt>{tier.minimum_quantity}–{tier.maximum_quantity ?? "∞"} fotos</dt><dd>{formatBrazilianCurrency(tier.unit_price_cents)} cada</dd></div>)}</dl>
              <div className="pricing-form-actions"><MarkinaButton variant="secondary" onClick={() => startEdit(preset)}>Editar</MarkinaButton>{preset.active ? <MarkinaButton variant="quiet" onClick={() => setActive(preset, false)}>Desativar</MarkinaButton> : <MarkinaButton variant="secondary" onClick={() => setActive(preset, true)}>Ativar</MarkinaButton>}</div>
            </SurfaceCard>
          ))}
        </section>
      </div>
    </div>
  );
}
