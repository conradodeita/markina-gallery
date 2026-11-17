# Proposal

## Why

O painel do fotógrafo exibe, no bloqueio de novos uploads, uma explicação técnica sobre a carteira consultada pelo servidor e a API. Esse detalhe não ajuda a resolver o problema. A seção de publicação também usa “Ritual”, termo que não descreve com clareza uma prática de trabalho.

## What Changes

- Mostrar “Saldo insuficiente para novos uploads” e um link “Adquira um pacote →” que leva diretamente aos pacotes de créditos na Visão Geral e em Créditos.
- Substituir “Ritual de publicação” por “Prática de publicação”, preservando as etapas atuais.
- Não alterar regras de saldo, compras, uploads ou publicação.

## Capabilities

### New Capabilities

- `photographer-dashboard-clarity`: comunicação direta dos estados de saldo e da prática de publicação no painel.

### Modified Capabilities

Nenhuma.

## Impact

Somente textos e links no painel administrativo do fotógrafo, o destino da seção de pacotes e os testes de interface correspondentes. Sem alteração de API, carteira, elegibilidade ou processamento de uploads.
