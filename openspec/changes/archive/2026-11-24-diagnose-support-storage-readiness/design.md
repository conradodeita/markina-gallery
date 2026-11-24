# Design

## Context

Veja `proposal.md` para a motivação. Hoje o snapshot protegido contém `state_directory_state` e `backup_directory_state`; o inventário imprime esses estados agregados, e a fingerprint é o hash do snapshot. `directory_invalid` pode ser causado por verificações distintas do alvo. `prepare-support` e `restore-support` aceitam somente os estados agregados `ready` e `creatable`.

## Goals / Non-Goals

**Goals:**

- Expor a razão sanitizada no mesmo inventário protegido, sem um novo canal ou privilégio.
- Vincular as razões ao fingerprint e manter estável a ordem de sua serialização.
- Preservar os estados agregados como única entrada dos gates de preparação e restauração.

**Non-Goals:**

- Determinar ou executar uma correção no host.
- Refinar causas internas de `parent_invalid`, inspecionar conteúdo, ou mostrar valores brutos de filesystem.
- Alterar ponte, wrapper, checkout, containers, configuração, Drive, serviço, timer ou dados.

## Decisions

1. **Preservar o contrato agregado e acrescentar diagnósticos.** O snapshot terá listas `state_directory_diagnostics` e `backup_directory_diagnostics`; a saída do inventário será `support_state_directory_diagnostics` e `support_backup_directory_diagnostics`. Os valores permitidos são `ready`, `creatable`, `parent_invalid`, `unavailable`, `target_symlink`, `target_type_invalid`, `target_owner_invalid`, `target_group_invalid` e `target_mode_invalid`. Para alvos inválidos, a lista contém todas as razões aplicáveis em ordem fixa; para os demais estados, contém somente a categoria agregada correspondente. A saída CLI serializa a lista como códigos separados por vírgula, sem texto livre.

   Alternativa rejeitada: substituir `directory_invalid` por novos estados. Isso acoplaria diagnóstico aos consumidores de estado e ampliaria o risco de mudar as guardas. Os códigos detalhados ficam em campos separados; o gate permanece baseado no estado agregado.

2. **Classificar usando somente metadados de `lstat`.** Um link simbólico produz somente `target_symlink` e nunca é seguido. Para qualquer outro alvo, `target_type_invalid` identifica um objeto que não é diretório; divergências de owner, grupo e modo acrescentam seus códigos fixos aplicáveis, sem expor os valores observados. Falhas de leitura produzem `unavailable`; causas de pai permanecem `parent_invalid`.

   Alternativa rejeitada: serializar caminho, UID/GID, owner/grupo, modo, `stat` bruto ou exceção. Esses dados não são necessários para escolher um procedimento e poderiam expor detalhes do host.

3. **Incluir diagnósticos em todos os snapshots protegidos relevantes.** `support-inventory` e `restore-support-inventory` retornam os mesmos campos diagnósticos que entram no objeto hasheado. Assim, qualquer mudança de estado ou razão invalida a fingerprint anterior. As verificações de elegibilidade continuam lendo somente `state_directory_state` e `backup_directory_state`, aceitando `ready`/`creatable` e recusando os demais antes de buscas ou gravações.

   Alternativa rejeitada: manter razões fora da fingerprint. Um relatório antigo poderia então ser apresentado após mudança nas condições do filesystem.

4. **Não automatizar a remediação.** O resultado serve apenas para orientar uma proposta posterior, se necessária. Qualquer alteração no host depende de fluxo protegido próprio, revisão/merge, CI da `main` no SHA exato, inventário/fingerprint atuais e autorização operacional específica.

## Risks / Trade-offs

- **Razões de pai continuam agregadas** → `parent_invalid` permanece uma categoria genérica; ampliar esse diagnóstico exige escopo e revisão separados. A ocorrência observada de `directory_invalid` recebe a distinção solicitada.
- **A fingerprint muda quando o contrato de snapshot muda** → qualquer aprovação anterior deixa de ser reutilizável e deve ser substituída por inventário read-only atual.
- **Categorias podem revelar que uma verificação falhou** → a saída usa apenas um conjunto fixo de enums e não mostra valores ou identificadores; nenhuma categoria altera o gate.

## Migration Plan

1. Após revisão humana dos artefatos, implementar e validar localmente a classificação e os campos de saída/fingerprint; atualizar testes e documentação da change.
2. Submeter a implementação em PR. Exigir revisão, merge autorizado e CI verde na `main` do SHA exato.
3. Depois, executar apenas um novo `support-inventory` read-only pelo fluxo protegido e com as aprovações exigidas pelo ambiente. Não encadear `prepare-support`.
4. Se uma futura remediação for necessária, especificá-la em change própria. Não usar shell/SSH ad hoc. Reversão da mudança de software segue o fluxo normal revisado; não há rollback de host associado a esta entrega.
