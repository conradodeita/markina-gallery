## Why

A homologação já dispõe de autenticação, modelo de galeria-mãe, pastas e referências privadas, porém o fotógrafo ainda não consegue executar e conferir visualmente o ciclo administrativo básico sem telas incompletas ou ações técnicas. Antes de validar venda, WhatsApp ou biometria, é necessário tornar a criação, organização, revisão e compartilhamento de uma galeria de teste realmente utilizável de ponta a ponta.

## What Changes

- Completar o fluxo administrativo contextual de galeria-mãe: criação, retorno seguro entre etapas, resumo e retomada da edição.
- Permitir criar pastas exclusivamente dentro da galeria atual, enviar JPEGs, acompanhar contagem e processamento, abrir a pasta, ver prévias protegidas com marca d’água, ampliar a prévia e excluir fotos sem histórico de compra.
- Permitir escolher e alterar capa da galeria a partir de foto autorizada; enquanto nenhuma for escolhida, usar a primeira foto disponível apenas como prévia padrão.
- Completar o vínculo de clientes na galeria atual: lista alfabética, busca por nome ou WhatsApp, vínculo de cadastro existente, criação de cliente e resumo dos vínculos e do link não listado.
- Exibir na área administrativa somente dados e comandos permitidos pelo backend, incluindo motivos para não permitir exclusão de foto.
- **BREAKING**: a exclusão de uma foto sem compra passa a remover suas referências administrativas elegíveis; fotos com compra confirmada permanecem protegidas e não podem ser excluídas pelo fluxo comum.
- Manter explicitamente fora desta mudança: WhatsApp, reconhecimento facial, precificação/carrinho/PIX e confirmação de venda.

## Capabilities

### New Capabilities

- `media-storage/admin-folder-photo-management`: gestão administrativa contextual de pastas, fotos, prévias protegidas, capa e exclusão segura antes de compra.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: o fluxo administrativo passa a exigir navegação completa por galeria-mãe, resumo, busca/vínculo de clientes e estados acionados pelo backend.

## Impact

- Backend FastAPI: contratos de foto, prévia, ampliação, exclusão protegida, capa, resumo de galeria e busca/vínculo de clientes.
- Modelo e migration: metadados de capa, e validação de exclusão preservando pedidos e histórico.
- Frontend Next.js: editor administrativo, página de resumo, gestão de pasta/foto e lista de clientes.
- Testes e homologação: fluxo sintético completo com JPEGs de teste; nenhuma dependência de WhatsApp, biometria ou pagamentos.

## Relação com a change sucessora

Esta change documenta o fluxo administrativo entregue antes do ciclo de vida comercial completo. `improve-gallery-and-client-data-lifecycle` supersede a exclusão limitada a galeria vazia, a recusa permanente de remover mídia apenas por existir compra confirmada e a criação imediata de galeria privada ao simples vínculo. O comportamento sucessor SHALL usar operação idempotente acompanhável, histórico comercial independente e derivação por seleção ou criação administrativa explícita. A revisão visual humana pendente permanece válida somente para as superfícies já entregues.
