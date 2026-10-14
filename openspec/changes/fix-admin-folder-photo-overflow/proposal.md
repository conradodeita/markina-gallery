# Proposal

## Why

A captura enviada pelo proprietário mostra imagens e nomes longos ultrapassando os cards da etapa Imagens do editor administrativo em celular. A investigação anterior da galeria cliente não correspondia à tela afetada; o componente real usa `.folder-photo-grid`.

## What Changes

- Conter imagem, nome e controles na largura do card administrativo, inclusive com nomes longos sem espaços.
- Manter o nome completo disponível por quebra de linha e preservar o enquadramento de miniatura existente.
- Validar no navegador a troca para a segunda pasta, diferentes proporções de foto, larguras de celular e desktop, temas e seleção/ampliação.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: contenção responsiva dos cards administrativos de fotos das pastas.

## Impact

CSS da grade administrativa e QA sintético local. Sem alteração de API, arquivos de imagem, nomes persistidos, uploads, banco, regras de exclusão, frontend cliente ou infraestrutura. O inventário técnico solicitado em anexo é uma tarefa documental distinta; esta change trata exclusivamente do bug visual relatado e ilustrado depois. A publicação da branch não constitui deploy.
