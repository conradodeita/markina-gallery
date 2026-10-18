# Proposal

## Why

Na etapa 04, pastas de galerias privadas podem ser confundidas com pastas públicas porque a interface não identifica visualmente a cliente associada. O fotógrafo precisa reconhecer o destino privado de cada pasta antes de enviar ou processar fotos, evitando uploads e notificações no contexto errado.

## What Changes

- Exibir na etapa 04 uma seção separada para pastas de galerias privadas derivadas da galeria-fonte.
- Identificar cada galeria privada pela cliente principal e mostrar também os demais membros ativos quando houver compartilhamento.
- Manter pastas privadas separadas das pastas públicas e obter nomes e vínculos de uma resposta administrativa autorizada do backend.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: adicionar a identificação e listagem contextual das pastas privadas e de suas clientes na etapa 04.

## Impact

- Frontend do editor administrativo da galeria-fonte, etapa 04.
- Contrato autenticado de leitura administrativa para listar galerias privadas derivadas, pastas e membros autorizados no escopo da galeria-fonte.
- Testes de API e do editor; nenhum dado ou vínculo será alterado pela consulta.
