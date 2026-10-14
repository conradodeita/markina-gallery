## ADDED Requirements

### Requirement: Separação comercial por galeria

O sistema SHALL manter carrinho, pedido, comunicação, confirmação e estatísticas separados por cliente e Galeria pública, ainda que a mesma cliente compre fotos de várias pastas ou participe de várias galerias.

#### Scenario: Seleção em várias pastas da mesma galeria

- **WHEN** a cliente seleciona fotos de pastas distintas dentro da mesma galeria
- **THEN** todas integram o mesmo carrinho e podem compor um único pedido daquela galeria

#### Scenario: Seleções em galerias diferentes

- **WHEN** a cliente seleciona fotos em duas Galerias públicas
- **THEN** o sistema mantém dois fluxos comerciais independentes, sem combinar valores, prazo ou confirmação

### Requirement: Contadores derivados do estado persistido

O sistema SHALL contabilizar fotos selecionadas a partir das seleções vigentes e fotos compradas somente a partir de itens de pedidos confirmados. A consulta administrativa SHALL refletir seleção criada pela Galeria pública, privada ou resultado facial autorizado.

#### Scenario: Seleção pública cria privada

- **WHEN** a cliente seleciona duas fotos na Galeria pública e a privada correspondente é criada ou reutilizada
- **THEN** as consultas administrativas da origem e da privada retornam duas fotos selecionadas para aquela cliente

#### Scenario: Pedido ainda não confirmado

- **WHEN** as fotos estão em pedido aguardando pagamento ou com pagamento comunicado
- **THEN** permanecem selecionadas, mas não são contadas como compradas

