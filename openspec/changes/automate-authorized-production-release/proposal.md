# Proposal

## Why

O release repete a mesma CI completa em cada despacho manual, mesmo quando o SHA não mudou, e a revisão exige intervenções repetidas. Em 26/10/2026 o proprietário autorizou automatizar as etapas e a aprovação protegida dentro do fluxo de release autorizado.

## What Changes

- Reutilizar CI de push à main para o SHA exato, concluído com sucesso, em operações manuais elegíveis, sem repetir a suíte inteira para o mesmo SHA.
- Automatizar aprovação e continuidade quando houver autorização humana vigente para a operação e ambiente, preservando a proteção do GitHub, inventário, fingerprint, lock, backup e revalidações.
- Registrar inventário e plano antes da ação, falhar fechado em divergência ou falta de autorização, e confirmar schema, serviços e HTTPS após publicação.
- Manter o release 0090 em andamento independente desta mudança e não alterar a main enquanto seu preflight depende do SHA atual.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: evidência de CI reutilizável e execução automatizada dentro da autorização vigente.

## Impact

Classificação/consulta de CI, workflow de release, documentação operacional e testes. Não altera aplicação, dados, segredos, regras de branch ou recursos de terceiros. As mudanças de execução protegida só serão ativadas após revisão, CI e integração; a autorização não torna irrestritas futuras operações fora do escopo concedido.
