# Proposal

## Why

A página Estatísticas apresenta somente contagens de fotos, seleções sem compra confirmada e receita agregada. O fotógrafo precisa conferir pedidos e itens por galeria/pasta e comparar os dados exibidos com exports financeiros, enquanto o CSV de vendas exige autorização adicional do proprietário da plataforma.

## What Changes

- Evoluir os indicadores comerciais usando pedidos e itens efetivamente persistidos, com isolamento pelo tenant da sessão.
- Detalhar vendas por cliente, pedido, fotografia, pasta, preço registrado, pagamento e conta de destino declarada no contrato do produto.
- Gerar HTML autônomo para o fotógrafo e CSV estruturado para o proprietário a partir da mesma consulta filtrada.
- Revalidar no backend a identidade persistente do proprietário para o CSV, reutilizando o registro `platform_owner` e o contrato existente, sem alterar o Monitor do sistema.
- Separar seleções sem compra, pedidos pendentes e abandono. Abandono usa somente o prazo de expiração configurado e persistido para a galeria/cliente, sem prazo global adicional.
- Sinalizar divergências entre itens e pedido e não apresentar dados não persistidos como forma de pagamento, reembolso ou conta de destino.

## Capabilities

### New Capabilities

- `gallery-sales/sales-statistics`: dashboard comercial, regras de agregação, exportações reconciliáveis, isolamento por tenant e limites dos dados estatísticos.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: adicionar filtros, indicadores, estados e navegação para o dashboard comercial.

## Impact

- Backend: consulta compartilhada de estatísticas, endpoints do dashboard e HTML/CSV, autorização do proprietário e testes de isolamento financeiro.
- Frontend: `/admin/statistics`, filtros, indicadores, tabelas detalhadas e responsividade.
- Banco: sem alteração prevista; vendas e expiração usam snapshots e prazos já persistidos.
- Monitor do sistema: leitura somente para verificar o contrato existente; nenhum arquivo, rota, migration ou dado do Monitor será modificado.
