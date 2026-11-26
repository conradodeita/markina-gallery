# Proposal

> **Registro histórico — fluxo aposentado em 25/11/2026.** A consulta de identidade do runtime global descrita nesta change foi tornada obsoleta pela retirada do código exclusivo na PR #436 (`eff4d504`). Não reativar este fluxo. A retirada remanescente está em `retire-platform-backup-runtime`; a nova prova de backup/recuperação está em `prove-open-source-backup-and-recovery`. O conteúdo abaixo permanece apenas para rastreabilidade; nenhuma spec principal compartilhada foi removida.

## Why

O inventário protegido continua recusando corretamente a identidade dos containers de API e web: o diagnóstico atual encontra vários registros parados por serviço, enquanto verificações separadas confirmaram os endpoints da aplicação. As contagens existentes não mostram se esses registros correspondem ao Compose atualmente implantado; uma comparação agregada pode explicar a divergência sem escolher uma identidade nem relaxar o gate.

## What Changes

- Ampliar o diagnóstico protegido somente de leitura para comparar, por serviço fixo, os registros que correspondem aos labels do projeto autorizado com os registros enumerados pela configuração Compose atual.
- Retornar somente contagens agregadas de correspondências e diferenças; manter IDs, nomes, labels, caminhos, saídas brutas, exceções e configuração fora da resposta e dos logs.
- Preservar a recusa do inventário normal quando não houver exatamente um ID completo por serviço. O diagnóstico não selecionará, removerá, corrigirá nem aprovará containers e não emitirá fingerprint ou precondições.
- Não alterar aplicação, Compose, banco, configuração do Drive, vínculo do destino, ensaio, cópia, restauração, serviço ou timer.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: acrescentar um diagnóstico protegido e agregado que compare registros do runtime com o Compose atual sem autorizar identidade ou mutação.

## Impact

Afeta o inventário operacional protegido de containers, seu contrato de resposta, testes, workflow e guardas de CI/OpenSpec. Não altera API/web da aplicação, schema, recursos Docker, configuração do host ou dados. Qualquer consulta no servidor continuará read-only e sujeita ao canal protegido já existente.
