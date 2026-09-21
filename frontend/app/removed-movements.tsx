export type RemovedMovement = {
  id: string; kind: string; client_name: string; gallery_name: string;
  parent_gallery_name: string; folder_name: string; filename: string;
  occurred_at: string; removed_at: string;
};

const labels: Record<string, string> = {
  selected: "Selecionada, sem compra neste movimento",
  favorited: "Favoritada", viewed: "Visualizada", commented: "Comentada",
};

export function RemovedMovements({ items, admin = false }: { items: RemovedMovement[]; admin?: boolean }) {
  if (!items.length) return null;
  return <section className="admin-card" aria-label="Histórico de acervo removido">
    <h2>Histórico de acervo removido</h2>
    <p>Referências dos movimentos anteriores à exclusão. Os pagamentos permanecem nos registros de pedidos.</p>
    <ul>{items.map((item) => <li key={item.id}>
      <strong>{item.filename}</strong> — {labels[item.kind] ?? item.kind}
      <p>{admin ? `${item.client_name} · ` : ""}{item.parent_gallery_name} · {item.gallery_name} · {item.folder_name}</p>
      <time dateTime={item.occurred_at}>{new Date(item.occurred_at).toLocaleString("pt-BR")}</time>
    </li>)}</ul>
  </section>;
}
