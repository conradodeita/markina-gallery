## Why

A aparência clara e escura atende ao uso atual, mas falta uma escolha de identidade visual entre superfícies neutras e acabamentos metálicos. O fotógrafo e o cliente devem poder selecionar uma paleta controlada sem comprometer legibilidade, acessibilidade ou a apresentação fiel das fotografias.

## What Changes

- Acrescentar ao seletor de aparência os acabamentos Cinza metálico, Azul metálico e Vinho metálico, coordenando gradientes discretos de superfície e cores de texto.
- Manter o acabamento neutro atual como opção padrão e permitir combinar o acabamento escolhido com Claro, Escuro ou Sistema.
- Persistir a escolha no navegador, sem vinculá-la a uma conta ou galeria.
- Restringir superfícies e cores de texto a tokens aprovados por acabamento e modo, com contraste legível e sem efeitos sobre fotografias, logos, favicons ou QR Codes.

## Capabilities

### New Capabilities

<!-- Nenhuma. -->

### Modified Capabilities

- `appearance-preference`: escolha e persistência de acabamentos visuais metálicos junto ao modo claro/escuro existente.

## Impact

Seletor de aparência, tokens CSS e superfícies compartilhadas do frontend. Não exige alterações de backend, banco de dados, APIs ou dependências externas.

## Goals / Non-Goals

**Goals:** oferecer os três acabamentos pedidos em todo o sistema, coordenar cores de superfície e texto, preservar a escolha Claro/Escuro/Sistema e manter contraste e cores de mídia.

**Non-Goals:** editor de cores ou gradientes livres, personalização por componente/galeria/conta, alteração da identidade das fotografias ou adição de acabamentos não especificados nesta change.

## Assumptions

- “Opções extras” significa incluir as três novas opções metálicas além do acabamento neutro já existente. Novos acabamentos não nomeados não serão inventados nesta change.
- O acabamento é independente do modo Claro/Escuro/Sistema e pode ser alterado separadamente; os gradientes metálicos são aplicados às superfícies claras, enquanto o modo escuro mantém superfícies escuras legíveis e usa a paleta escolhida de forma compatível nos realces.

## Risks / Trade-offs

- Gradientes e cores de texto podem reduzir contraste ou competir com conteúdo; usar pares de tokens aprovados e manter fundos de texto e controles suficientemente uniformes.
- Preferências locais podem não acompanhar o usuário entre dispositivos; essa escolha evita persistir uma nova configuração de conta ou introduzir backend para uma personalização cosmética.
