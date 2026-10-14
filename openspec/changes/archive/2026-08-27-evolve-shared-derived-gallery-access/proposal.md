## Why

Uma galeria privada possui uma cliente proprietária, mas o negócio exige que mãe, pai e outros responsáveis autorizados possam revisar o mesmo conjunto de fotos com seleções, pedidos e compras independentes. O fotógrafo também precisa localizar e conduzir essas galerias por estado operacional, sem expor o acervo coletivo.

## Status

**Supersedida em 2026-08-28.** Não implementar esta proposta. A decisão arquitetural vigente é `add-cloned-private-gallery-ownership`: cada responsável recebe uma galeria privada clonada, com propriedade e histórico comercial isolados. Esta proposta conflita com esse modelo ao permitir múltiplos responsáveis na mesma galeria derivada e é preservada somente para histórico de decisão.

## What Changes

- Evoluir a galeria derivada para aceitar vários responsáveis autorizados, preservando acesso, seleção, favoritos, comentários, pedidos e histórico isolados por responsável.
- Preservar a cliente proprietária da galeria e adicionar vínculos individuais para responsáveis adicionais, com estados ativos, bloqueados e expirados, sem apagar o histórico comercial.
- Criar uma superfície administrativa backend-driven de galerias com busca por nome ou telefone, ordenação operacional, filtros de seleção/pagamento/acesso/prazo e abas de galerias ativas e congeladas.
- Criar ficha administrativa da galeria para copiar o link controlado, vincular ou criar responsável, bloquear/liberar acesso individual e reativar prazo expirado.
- Preservar os vínculos já existentes na migração aditiva: o cliente principal atual torna-se um responsável autorizado, sem concessão indevida a terceiros.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `client-access/derived-galleries`: permitir acesso compartilhado à galeria derivada com isolamento dos dados de cada responsável e ciclo de acesso individual.
- `gallery-sales/operational-gallery-interface`: fornecer gestão administrativa de galerias por estado operacional, responsáveis vinculados, bloqueio e reativação de prazo.

## Impact

- Modelos, migration aditiva, autorização, APIs e testes FastAPI de galerias derivadas e vínculos de acesso.
- Rotas e componentes Next.js da lista e ficha de galerias administrativas, sempre orientados pelo backend.
- A mudança não implementa pastas, importação em lote, preço progressivo, checkout, mensagens, branding, cartão, entrega ou reconhecimento facial; esses itens permanecem em mudanças próprias ou futuras.
