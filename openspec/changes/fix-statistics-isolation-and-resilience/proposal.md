# Proposal

## Why

A auditoria da página administrativa `Estatísticas` encontrou quatro riscos operacionais: filtros por cliente que podem misturar membros de uma galeria compartilhada, identificadores inválidos quando a mídia operacional foi removida, listas limitadas sem paginação e falhas de API exibidas como receita zero. Os mesmos agregados alimentam os dois exports TXT, portanto a correção precisa abranger a superfície HTML e os arquivos baixados antes de considerar a área confiável para decisão financeira.

## What Changes

- Corrigir o escopo dos agregados para filtrar seleções e pedidos pelo cliente efetivamente consultado, preservando a separação por cliente e Galeria pública.
- Usar `photo_asset_id_snapshot` e `filename_snapshot` nos pedidos confirmados quando o ativo operacional não existir mais, mantendo exports textuais válidos e sem URLs ou PII.
- Expor paginação explícita para as listas administrativas de fotos compradas e selecionadas sem compra, sem alterar a contagem total nem o conteúdo completo dos exports.
- Diferenciar erro de carregamento de estado vazio na página, com mensagem acessível e ação de nova tentativa.
- Reforçar testes de isolamento entre membros, histórico após exclusão, paginação, falhas de API e exports TXT filtrados.

## Capabilities

### New Capabilities

- `gallery-sales/sales-statistics`: contrato consolidado para agregação, isolamento, paginação, estados de erro e exportação textual das estatísticas administrativas.

### Modified Capabilities

- `gallery-sales/client-selection-operations`: exports e contadores SHALL respeitar o cliente e preservar identificadores textuais de pedidos após remoção do ativo operacional.
- `gallery-sales/operational-gallery-interface`: a superfície administrativa de estatísticas SHALL distinguir falha de consulta, estado vazio e resultados paginados.

## Impact

- Backend: `statistics_data`, endpoints administrativos de estatísticas e exports TXT, consultas de pedidos/seleções e snapshots comerciais.
- Frontend: página `/admin/statistics`, estado de erro, retry, paginação e links de exportação.
- Testes backend/frontend e documentação OpenSpec; nenhuma migration, alteração de segredo, deploy ou mudança de infraestrutura.
