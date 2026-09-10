import Link from "next/link";

export type ClientCartItem = {
  id: string;
  name: string;
  previewUrl?: string | null;
};

export function ClientCartLink({ count, href, className = "client-cart-link" }: { count: number; href: string; className?: string }) {
  if (count < 1) return null;
  return <Link className={className} href={href}>Carrinho ({count})</Link>;
}

export function ClientCartItems({ items, onRemove }: { items: ClientCartItem[]; onRemove?: (photoId: string) => void }) {
  if (!items.length) return null;
  return (
    <ul className="client-cart-items" aria-label="Fotos no carrinho">
      {items.map((item) => (
        <li key={item.id}>
          {item.previewUrl ? <img src={item.previewUrl} alt={`Miniatura protegida de ${item.name}`} draggable={false} /> : null}
          <span>{item.name}</span>
          {onRemove ? <button type="button" className="link-button" aria-label={`Remover ${item.name} do carrinho`} onClick={() => onRemove(item.id)}>Remover</button> : null}
        </li>
      ))}
    </ul>
  );
}
