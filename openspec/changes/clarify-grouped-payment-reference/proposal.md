# Proposal

## Why

No checkout agrupado, a mensagem de pagamento e “Compras” identificam a compra pelo código do grupo PIX, enquanto o painel do fotógrafo mostra códigos dos pedidos individuais por galeria. Além de dificultar localizar o pagamento, templates de galeria única podem produzir textos contraditórios como “da galeria sua compra” quando o pagamento cobre um grupo.

## What Changes

- Identificar no painel financeiro a referência da compra agrupada com o mesmo código curto já usado nas mensagens e em “Compras”.
- Mostrar, sob essa referência, os pedidos por galeria com seus códigos existentes, valores e composição, deixando explícita a relação entre compra e pedidos.
- Apresentar confirmação, recusa e correção como ações sobre a compra agrupada, indicando as galerias/pedidos abrangidos; manter a operação individual dos pedidos sem agrupamento.
- Renderizar mensagens de pagamento com texto contextual correto: compra agrupada quando houver PIX único e pedido da galeria quando o pedido for individual. A referência continuará usando o identificador já existente.
- Preservar IDs e relações persistidos em produção. Não criar novos códigos, reidentificar pedidos, reagrupar histórico nem reescrever mensagens/notificações já emitidas ou snapshots de entrega.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: explicitar a referência da compra agrupada e sua composição no painel financeiro e apresentar contexto coerente nas mensagens de pagamento.

## Impact

Impacta a apresentação do painel administrativo de vendas e pagamentos, a renderização dos templates transacionais de pagamento e, se necessário, a projeção existente dos grupos e pedidos. Não requer mudança de modelo nem migration de schema. A configuração ativa de templates poderá exigir uma transformação de texto estritamente delimitada e revisável; snapshots e mensagens históricas ficam inalterados. Códigos e relações persistidos em produção permanecem iguais.
