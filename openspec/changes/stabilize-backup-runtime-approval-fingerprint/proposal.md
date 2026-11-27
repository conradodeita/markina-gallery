# Proposal

> **Registro histórico — contrato de runtime aposentado em 25/11/2026.** A fingerprint de aprovação do runtime global descrita nesta change não é mais usada desde a retirada do código exclusivo na PR #436 (`eff4d504`). Não reativar este fluxo. A retirada remanescente está em `retire-platform-backup-runtime`; a nova prova de backup/recuperação está em `prove-open-source-backup-and-recovery`. A fingerprint genérica ainda usada pelos workflows compartilhados de suporte é outro contrato e deve ser preservada. O conteúdo abaixo permanece apenas para rastreabilidade.

## Why

As tentativas protegidas de `install` #45494495527 e #45500760778 foram interrompidas antes de transferir o artefato, iniciar SSH ou escrever no host porque a fingerprint integral mudou somente com pequenas variações de espaço livre em `/var/lib` (296 KiB e 104 KiB). No run #45500760778, o inventário atual ainda mostrou precondições `pass`, serviços saudáveis, schema `20261113_0126` e 133717640 KiB livres (35% usados), mas a diferença exata de espaço invalidou a aprovação. O gate precisa continuar bloqueando espaço insuficiente sem exigir nova aprovação humana por cada oscilação inofensiva dessa métrica.

## What Changes

- Separar a identidade estável que o proprietário aprova das medições voláteis de capacidade do disco.
- Manter na fingerprint aprovada a identidade do host/runtime, o estado e a identidade dos containers, schema, configurações protegidas e identidade/capacidade total dos filesystems de `/var/lib`, `/opt/pyp-backup-runtime` e `/etc/systemd/system`; verificar o vínculo da conexão protegida, SHA/CI e hash do pacote separadamente no mesmo gate.
- Continuar apresentando a capacidade atual de cada destino no inventário e validá-la novamente sob o lock antes da primeira escrita e imediatamente antes da troca ativa; espaço acima do limite operacional ou insuficiente para o bound do pacote, staging, instalação e rollback SHALL bloquear a operação mesmo quando a fingerprint estável corresponder.
- Versionar e nomear claramente os valores de fingerprint para impedir que aprovações antigas de inventário integral sejam aceitas como aprovação do novo contrato.
- Atualizar a cópia fixada do forced command SSH para reconhecer o novo fingerprint e sua saída, mantendo o binding antigo para `bind-and-rehearse` e `reconcile`; a atualização remota do wrapper permanece em operação protegida separada após review/merge/CI.
- Preservar o fluxo de revisão, merge, CI da `main`, novo inventário, aprovação humana da fingerprint e aprovação separada do ambiente `production` antes de qualquer nova operação de produção.

## Capabilities

### New Capabilities

- `deployment-operations/backup-runtime-approval`: aprovação protegida do runtime de backup vinculada a identidade operacional estável e a precondições de capacidade revalidadas em tempo real.

### Modified Capabilities

Nenhuma. O contrato novo será isolado do gate integral de outros workflows de produção.

## Impact

Afeta o inventariador e o instalador do runtime de backup, o workflow protegido correspondente, o forced command SSH e seu workflow protegido de atualização, testes e documentação OpenSpec. Não altera a política de fingerprints das demais operações, o pacote do runtime, aplicações, banco ou configuração de backup. Esta change não despacha operações, não acessa o host/Drive e não instala o wrapper, runtime, vínculo, backup ou timer; qualquer execução futura continua sujeita aos gates e aprovações próprios.
