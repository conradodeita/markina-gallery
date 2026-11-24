# Proposal

## Why

O inventário protegido mais recente identificou que o diretório fixo de cópias anteriores está com modo diferente do contrato `root:root 0700`. `prepare-support` corretamente recusa esse estado; é necessário um fluxo protegido e explícito para corrigir somente essa divergência sem alterar conteúdo ou ampliar a operação de preparação.

## What Changes

- Introduzir a operação allowlisted `repair-support-backups-mode`, separada, para ajustar ao modo `0700` somente o diretório fixo de cópias de suporte quando o inventário atual confirmar `target_mode_invalid` como única divergência do alvo.
- Exigir CI verde da `main` no SHA exato, fingerprint atual aprovada e ambiente protegido `production`; rejeitar caminhos, comandos ou modos fornecidos pelo operador.
- Revalidar identidade, tipo, owner/grupo, pai, modo e fingerprint sob o lock comum antes da alteração; preservar a identidade, owner/grupo e todos os conteúdos do diretório.
- Emitir resultado sanitizado e exigir um novo `support-inventory` read-only antes de qualquer `prepare-support`. A operação SHALL NOT preparar suporte, trocar executáveis ou refs, acessar Drive, instalar runtime ou alterar serviços/timers.
- Abortos por tipo, owner/grupo, link simbólico, pai, fingerprint ou estado inesperado permanecem fail-closed e não tentam reparo automático.

## Capabilities

### New Capabilities

- `deployment-operations/backup-runtime-support-remediation`: ajuste protegido e limitado do modo do diretório fixo de cópias do suporte do preflight.

### Modified Capabilities

Nenhuma. A nova operação é separada; inventário e preparação atuais mantêm seus contratos.

## Impact

- Afeta o helper `scripts/production_app_preflight_support.py`, o workflow protegido `production-app-compose-bridge-install.yml` e os testes estáticos/sintéticos correspondentes.
- No host, a operação poderá alterar somente o modo do diretório fixo já existente, de uma permissão divergente para `0700`, sob a aprovação operacional futura. Conteúdo, owner, group, caminhos, refs, executáveis, containers, aplicação, banco, Drive, runtime de backup, serviço e timer ficam fora do escopo.
- A implementação local e a CI não despacham a operação. Qualquer execução remota continua condicionada a revisão/merge, CI verde no SHA exato, novo inventário/fingerprint e autorização operacional específica.
