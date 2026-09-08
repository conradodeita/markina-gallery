## Why

As telas atuais permitem testar contratos isolados, mas não dão ao fotógrafo nem à cliente uma experiência contínua e reconhecível como produto final. A validação precisa ocorrer em uma interface autoral, responsiva e conectada a dados reais do backend, para que decisões e relatos de uso sejam confiáveis antes de avançar para pagamento e comunicação.

## What Changes

- Substituir as superfícies provisórias por uma experiência visual original e coerente para fotógrafo e cliente, preservando as permissões e contratos existentes.
- Organizar a operação do fotógrafo em dashboard, lista e ficha de acervos/galerias, clientes, pastas e carregamento de JPEGs, com estados explícitos de preparação, falha e liberação.
- Criar a jornada visual da cliente com biblioteca, grade protegida, ampliador, seleção, favoritos, comentários, prazo e histórico privado.
- Introduzir liberação explícita de uma pasta/lote: fotos em preparação não chegam à cliente; fotos posteriores formam uma nova pasta e nova rodada de revisão.
- Permitir exclusão administrativa somente de itens sem histórico relevante, preservando compras confirmadas por congelamento/bloqueio em vez de remoção.
- Padronizar componentes, responsividade, acessibilidade e estados de carregamento, vazio, erro, bloqueio, expiração e sucesso, sempre orientados pelo backend.

## Capabilities

### New Capabilities

- `gallery-sales/original-gallery-experience`: experiência visual original e backend-driven para a operação do fotógrafo e a jornada privada da cliente.
- `media-storage/staged-folder-release`: preparação e liberação controlada de pastas de fotos, sem exposição antecipada a clientes.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: ampliar o fluxo administrativo para gestão visual completa de acervos, galerias, clientes, pastas e mídia.
- `client-access/derived-galleries`: ampliar a biblioteca e a galeria privada da cliente com navegação visual, estados privados e histórico acessível.

## Impact

- Frontend Next.js, design system interno, contratos FastAPI de resumo operacional, pastas e upload/liberação de mídia, além de testes de componente e API.
- Não inclui checkout/PIX, envio real de WhatsApp, busca facial, originais, grade pública de evento coletivo ou alteração de infraestrutura.
- A homologação usará somente JPEGs e dados sintéticos e continuará limitada ao projeto Docker `markina-gallery`.
