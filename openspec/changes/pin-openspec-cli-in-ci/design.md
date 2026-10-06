# Design

## Context

O workflow `.github/workflows/ci.yml` instala OpenSpec por `@latest` e executa `validate --strict --all`. A resolução muda fora do Git; em 2026-10-06, 1.14.1 retornou 25 falhas em changes/specs existentes, enquanto 1.14.0 validou 77/77 itens no mesmo checkout.

## Goals / Non-Goals

**Goals:**

- Tornar a validação OpenSpec do CI reproduzível a partir do próprio commit.
- Preservar a validação estrita de todas as changes e specs.
- Deixar a versão validada e o processo de atualização claros no repositório.

**Non-Goals:**

- Corrigir, arquivar ou enfraquecer as 25 verificações preexistentes que falham em 1.14.1.
- Alterar comportamento de aplicação, schema de dados, imagens Docker ou deploy de homologação.
- Manter o OpenSpec indefinidamente em 1.14.0 sem revisões futuras.

## Decisions

### Versão exata no workflow

O comando do job OpenSpec usará `@1.14.0` no lugar de `@latest`. Essa é a versão que reproduziu localmente o resultado verde de 77/77 itens. O comando continuará executando `validate --strict --all` sem filtros.

Alternativa rejeitada: conservar `@latest`, pois uma publicação externa alterou o resultado do CI sem qualquer alteração do repositório. Também rejeitamos reduzir o conjunto validado, remover `--strict` ou suprimir avisos.

### Atualização explícita do validador

Uma futura versão só substituirá 1.14.0 após uma alteração revisada que rode `validate --strict --all` sobre a árvore integral e registre o resultado; divergências de validação deverão ser corrigidas ou resolvidas explicitamente antes da troca.

## Risks / Trade-offs

- A versão fixada não recebe novas correções do CLI automaticamente; atualizações deliberadas serão necessárias.
- O pin só é confiável se o CI usar a mesma versão exata e mantiver o comando estrito completo; a revisão do diff e a validação integral verificam esses pontos nesta change.
