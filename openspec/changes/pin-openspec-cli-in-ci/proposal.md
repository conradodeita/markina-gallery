# Proposal

## Why

O workflow de CI resolve OpenSpec por `@latest`, fazendo o gate estrito mudar sem alteração no repositório. A versão 1.14.1, publicada em 2026-10-05 23:28 UTC, passou a reprovar 25 mudanças já existentes; a versão 1.14.0 passou 77/77 itens no mesmo checkout.

## What Changes

- Fixar a versão do OpenSpec usada pelo workflow de CI em uma versão exata validada.
- Preservar `validate --strict --all`; não ignorar avisos, reduzir escopo de validação nem alterar specs alheias.
- Tratar futuras atualizações do CLI como alteração explícita, validada antes de trocar a versão fixada.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

Nenhuma. Esta mudança afeta somente a ferramenta de validação de desenvolvimento; não altera o comportamento do produto em runtime.

## Impact

- `.github/workflows/ci.yml`: resolução determinística da dependência CLI do OpenSpec.
- CI: resultado reproduzível sem enfraquecer lint, testes, build ou validação estrita.
- Nenhum efeito em APIs, banco, dados, imagens Docker ou ambiente de homologação.
