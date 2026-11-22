import { MarkinaLink } from "../../ui-kit";

export function CreditShortfallNotice() {
  return <div className="mk-state mk-state--error" role="alert">
    <strong>Saldo insuficiente para novos uploads</strong>
    <p><MarkinaLink href="/admin/credits#credit-packages" variant="quiet">Adquira um pacote →</MarkinaLink></p>
  </div>;
}
