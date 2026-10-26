# Design

## Context

A intensidade é atualmente limitada a 10–75% em três contratos de persistência, endpoints Pydantic, validação de pasta e slider. O motor mistura a prévia limpa e a corrigida com `Image.blend(clean, corrected, strength / 100)`. Portanto, 100% seleciona a saída corrigida inteira; não altera os EVs nem significa aumento de exposição.

## Goals / Non-Goals

**Goals:** permitir escolher até 100% mantendo consistência entre armazenamento, API, domínio e UI; preservar defaults e valores existentes.

**Non-Goals:** mudar o algoritmo automático, ativar recursos novos do RawTherapee ou reprocessar resultados existentes.

## Decisions

1. Alterar para 10–100% os limites de `preview_adjustment_settings.strength`, `gallery_preview_settings.strength` e `folder_processing_settings.preview_strength`. As duas primeiras tabelas são contratos legados ainda presentes no metadata e não devem permanecer com limites divergentes.
2. Criar migration Alembic `0090` descendente de `20261025_0089` que substitui apenas as três CHECK constraints. Não atualizar linhas, geração, filas nem imagens.
3. No downgrade, verificar primeiro se há valor acima de 75 em qualquer tabela. Se houver, interromper antes de alterar constraints, sem truncar nem corrigir valores automaticamente.
4. Atualizar ambos os contratos de API, validação de domínio, slider e documentação para o limite superior 100. Manter o passo de 5 pontos, mínimos de 10%, defaults 50/75% e exposição separada.
5. Validação local: frontend focado passou (9 testes), ESLint, TypeScript e Ruff passaram; backend teve 24 testes aprovados e os 3 testes focados da migration passaram. Nove cenários de API não iniciaram porque o ambiente local não contém o pacote `mercadopago`; o CI deve validar esses cenários com as dependências completas. A migration não foi executada em banco operacional.

## Risks / Trade-offs

- Em 100%, a prévia deixa de conter a mistura visual de 25–90% com a imagem limpa; o resultado pode parecer mais intenso. Isso é a semântica solicitada, sem prometer qualidade estética.
- Clientes com código antigo ainda aceitam os valores anteriores; o servidor atualizado é quem controla a faixa superior persistida. O downgrade é seguro somente quando nenhum registro excede 75.

## Migration Plan

Criar revision Alembic após `20261025_0089`; na upgrade, substituir as três constraints com limites 10–100. Na downgrade, bloquear se existir valor acima de 75 e, caso contrário, restaurar constraints antigas. Após CI verde e merge, a migration será aplicada pelo fluxo autorizado de release, com preflight operacional, backup e smoke do procedimento vigente.
