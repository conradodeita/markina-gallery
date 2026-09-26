# Proposal

## Why

As fotos adicionadas a uma galeria privada já usam o pipeline comum de derivados, mas as grades administrativa e da cliente requisitam todas as prévias protegidas assim que são renderizadas. Em pastas extensas, isso concentra transferências de JPEGs de até 1600/1980 px e torna a abertura lenta, sobretudo no celular.

## What Changes

- Adiar o carregamento das imagens fora da área visível nas grades da galeria privada do fotógrafo e da cliente.
- Preservar a prévia protegida existente, a ampliação em resolução atual e todas as regras de acesso, geração, armazenamento e marcas d'água.
- Documentar que a mudança reduz requisições iniciais, não os bytes de cada derivado nem o custo de upload/geração.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `client-access/derived-galleries`: carregamento progressivo da grade privada.
- `gallery-sales/operational-gallery-interface`: carregamento progressivo das miniaturas no painel da galeria privada.

## Impact

Somente componentes de apresentação frontend e testes. Sem mudança de API, banco, arquivos existentes, pipeline de mídia, galeria pública, integrações ou infraestrutura. O trabalho local em outras mudanças permanece fora deste escopo.
