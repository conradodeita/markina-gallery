# Proposal

## Why

O mesmo card de diagnóstico aparece na Visão Geral e no Monitor do Sistema. O proprietário solicitou em 10/10/2026 manter apenas a segunda ocorrência.

## What Changes

- Retirar o card e sua montagem da Visão Geral.
- Manter diagnóstico, atualização manual, cópia e autorização no Monitor do Sistema.
- Identificar fotógrafos na árvore por e-mail já cadastrado, conforme orientação final do proprietário: apenas e-mail, sem novo campo de nome.
- Proteger localização, identificação e privacidade por regressões.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations/admin-capacity-diagnostics`: localização exclusiva do card e da cópia no Monitor do Sistema.

- `auth/administrative-activity`: identificação legível por e-mail restrita à árvore privilegiada.

## Impact

Frontend administrativo, projeção da árvore no backend e testes existentes, sem migration ou configuração. A instrução humana de retirar o card autoriza preparar e implementar esta mudança na mesma execução. Publicação pelo fluxo de PR/CI; pausar após push conforme orientação vigente. A change anterior do monitor foi consolidada e arquivada com aprovação própria.
