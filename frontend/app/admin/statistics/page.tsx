"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

type Option = {
  id: string;
  name: string;
  event_name?: string;
  client_id?: string;
};
type Statistics = {
  purchased_count: number;
  selected_not_purchased_count: number;
  revenue_cents: number;
  revenue_by_day: Array<{ date: string; revenue_cents: number }>;
  purchased_photos: Array<{ id: string; filename: string }>;
  selected_not_purchased_photos: Array<{ id: string; filename: string }>;
};
const emptyStatistics: Statistics = {
  purchased_count: 0,
  selected_not_purchased_count: 0,
  revenue_cents: 0,
  revenue_by_day: [],
  purchased_photos: [],
  selected_not_purchased_photos: [],
};

function currency(cents: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(cents / 100);
}

function RevenueChart({ points }: { points: Statistics["revenue_by_day"] }) {
  const maximum = Math.max(...points.map((point) => point.revenue_cents), 1);
  if (!points.length)
    return <p className="form-message">Nenhuma venda confirmada no período.</p>;
  return (
    <div
      className="revenue-chart"
      aria-label="Receita confirmada ao longo do tempo"
    >
      {points.map((point) => (
        <div className="chart-column" key={point.date}>
          <span
            style={{
              height: `${Math.max(8, (point.revenue_cents / maximum) * 100)}%`,
            }}
            title={`${point.date}: ${currency(point.revenue_cents)}`}
          />
          <small>
            {new Date(`${point.date}T00:00:00`).toLocaleDateString("pt-BR", {
              day: "2-digit",
              month: "2-digit",
            })}
          </small>
        </div>
      ))}
    </div>
  );
}

export default function StatisticsPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [options, setOptions] = useState<{
    clients: Option[];
    parent_galleries: Option[];
    derived_galleries: Option[];
  }>({ clients: [], parent_galleries: [], derived_galleries: [] });
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [data, setData] = useState<Statistics | null>(null);
  const query = useMemo(
    () =>
      new URLSearchParams(
        Object.entries(filters).filter(([, value]) => value),
      ).toString(),
    [filters],
  );
  function loadStatistics() {
    setData(null);
    fetch(`/api/admin/statistics${query ? `?${query}` : ""}`, {
      credentials: "same-origin",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setData(await response.json());
      })
      .catch(() => setData(emptyStatistics));
  }
  useEffect(() => {
    fetch("/api/admin", { credentials: "same-origin" })
      .then((response) => {
        setAuthorized(response.ok);
        if (response.ok) loadStatistics();
      })
      .catch(() => setAuthorized(false));
    fetch("/api/admin/statistics/filters", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        setOptions(await response.json());
      })
      .catch(() => undefined);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loadStatistics();
  }
  function update(name: string, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
  }
  if (authorized === null)
    return <main className="admin-shell">Carregando estatísticas…</main>;
  if (!authorized)
    return (
      <main className="admin-shell">
        <h1>Acesso restrito</h1>
        <Link href="/">Voltar para entrada</Link>
      </main>
    );
  return (
    <main className="admin-shell">
      <p className="eyebrow">Markina Gallery · Fotógrafo</p>
      <h1>Estatísticas</h1>
      <p className="intro">
        Acompanhe conversão e receita confirmada. Pedidos pendentes não entram
        nos valores.
      </p>
      <form className="filter-grid" onSubmit={apply}>
        <label>
          De
          <input
            type="date"
            onChange={(event) =>
              update(
                "starts_at",
                event.target.value ? `${event.target.value}T00:00:00Z` : "",
              )
            }
          />
        </label>
        <label>
          Até
          <input
            type="date"
            onChange={(event) =>
              update(
                "ends_at",
                event.target.value ? `${event.target.value}T23:59:59Z` : "",
              )
            }
          />
        </label>
        <label>
          Cliente
          <select onChange={(event) => update("client_id", event.target.value)}>
            <option value="">Todos</option>
            {options.clients.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Evento
          <input
            list="events"
            onChange={(event) => update("event_name", event.target.value)}
          />
          <datalist id="events">
            {options.parent_galleries
              .filter((item) => item.event_name)
              .map((item) => (
                <option key={item.id} value={item.event_name} />
              ))}
          </datalist>
        </label>
        <label>
          Galeria pública
          <select
            onChange={(event) =>
              update("parent_gallery_id", event.target.value)
            }
          >
            <option value="">Todos</option>
            {options.parent_galleries.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Galeria privada
          <select
            onChange={(event) =>
              update("derived_gallery_id", event.target.value)
            }
          >
            <option value="">Todas</option>
            {options.derived_galleries.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <button className="primary">Aplicar filtros</button>
      </form>
      {data === null ? (
        <p className="form-message">Atualizando indicadores…</p>
      ) : (
        <>
          <section className="stat-cards">
            <article>
              <span>Fotos compradas</span>
              <strong>{data.purchased_count}</strong>
            </article>
            <article>
              <span>Selecionadas sem compra</span>
              <strong>{data.selected_not_purchased_count}</strong>
            </article>
            <article>
              <span>Receita confirmada</span>
              <strong>{currency(data.revenue_cents)}</strong>
            </article>
          </section>
          <section className="admin-card">
            <h2>Receita no período</h2>
            <RevenueChart points={data.revenue_by_day} />
          </section>
          <section className="admin-card">
            <h2>Fotos compradas</h2>
            <a
              className="secondary"
              href={`/api/admin/statistics/purchased.txt${query ? `?${query}` : ""}`}
            >
              Baixar TXT
            </a>
            <ul className="photo-list">
              {data.purchased_photos.map((photo) => (
                <li key={photo.id}>
                  <code>{photo.id}</code>
                  {photo.filename}
                </li>
              ))}
            </ul>
            {!data.purchased_photos.length && (
              <p className="form-message">Nenhuma foto comprada.</p>
            )}
          </section>
          <section className="admin-card">
            <h2>Selecionadas, não compradas</h2>
            <a
              className="secondary"
              href={`/api/admin/statistics/selected-not-purchased.txt${query ? `?${query}` : ""}`}
            >
              Baixar TXT
            </a>
            <ul className="photo-list">
              {data.selected_not_purchased_photos.map((photo) => (
                <li key={photo.id}>
                  <code>{photo.id}</code>
                  {photo.filename}
                </li>
              ))}
            </ul>
            {!data.selected_not_purchased_photos.length && (
              <p className="form-message">Nenhuma seleção sem compra.</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}
