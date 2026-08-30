## Context

Veja `proposal.md`. Busca facial é proibida para clientes até validar privacidade, licença e desempenho ARM.

## Goals / Non-Goals

**Goals:** medir uma alternativa local, documentar controles e produzir decisão de gate.

**Non-Goals:** liberar recurso ao cliente, usar fotos reais de crianças ou integrar resultado a produção.

## Decisions

### Ambiente isolado e dataset seguro

O spike usará ambiente separado, dataset sintético/anonimizado e evento único. Nenhum embedding ou referência será reaproveitado.

### Gate mensurável

O relatório incluirá licença comercial, precisão, falso positivo/negativo, latência e consumo ARM; qualquer falha obrigatória bloqueia produto.

### Fluxo humano futuro

Mesmo aprovado, resultado futuro será privado, dependerá de consentimento específico e revisão do fotógrafo antes de gerar galeria derivada.

## Risks / Trade-offs

- [Risco biométrico] → não coletar dado real e exigir decisão jurídica posterior.
- [Modelo incompatível] → rejeitar alternativa, sem degradação de privacidade.

## Migration Plan

Sem migration de produção. Criar e destruir recursos isolados do spike; arquivar apenas relatório e decisão sem dados biométricos.
