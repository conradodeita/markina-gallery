# Design

## Context

Ver `proposal.md` para a motivação e a spec delta para os contratos observáveis. O helper atual classifica o diretório fixo `/var/backups/markina-gallery` como `ready` somente quando o alvo é `root:root 0700` e o pai imediato atende ao contrato `root:root 0755`. `support-inventory` é read-only e integra estado e razões na fingerprint. `prepare-support` aborta se qualquer diretório não estiver `ready` ou `creatable`. O workflow protegido já usa operação allowlisted, lock comum, CI no SHA de `main` e ambiente `production`.

## Goals / Non-Goals

**Goals:**

- Dar um caminho protegido e auditável para corrigir apenas uma divergência de modo já identificada por fingerprint atual.
- Preservar a semântica read-only do inventário e o fail-closed de `prepare-support`.
- Manter o limite operacional em um único diretório fixo e uma única alteração de permissão.

**Non-Goals:**

- Corrigir ownership, group, tipo, link simbólico, diretório pai ou estados indisponíveis; esses casos permanecem bloqueados para diagnóstico humano.
- Preparar suporte, restaurar helpers, atualizar refs, instalar runtime, vincular pasta, acessar Drive, executar backup/restore ou ativar serviço/timer.
- Realizar qualquer operação remota durante implementação, revisão ou CI.

## Decisions

1. **Adicionar uma operação fixa ao workflow protegido existente.** O input será `repair-support-backups-mode`; aceita apenas a fingerprint e nenhum caminho, comando, owner, group ou modo. A execução mantém `environment: production`, o SHA da `main` com CI verde, a conexão aprovada e o lock de release já usado pelo suporte. Reutilizar o canal evita duplicar credenciais e gates; corrigir dentro de `prepare-support` foi rejeitado porque ocultaria uma mutação distinta e contrariaria o contrato que exige abortar antes da preparação.

2. **Permitir apenas a classificação exata prevista.** Sob o lock, o helper coleta de novo o snapshot e compara a fingerprint completa. A operação prossegue somente se o diretório fixo existir, a única razão do alvo for `target_mode_invalid`, e pai, tipo, owner e group forem válidos. Alvo ausente, já correto, indisponível ou com qualquer outra divergência aborta sem escrita.

3. **Alterar por descritor e verificar a identidade.** Abrir o alvo fixo como diretório com recusa a symlink, validar `fstat`, aplicar `fchmod(0700)` ao descritor e confirmar modo, owner/group, tipo e identidade do inode. Não percorrer nem ler entradas. Comparar também a impressão dos containers e os demais elementos do snapshot que não podem mudar nesta operação.

4. **Não compensar uma alteração de modo não comprovada.** `fchmod` é a única mutação desta operação. Se qualquer verificação posterior falhar, parar sem retry ou limpeza e emitir somente `support_backup_mode_unverified`; não tentar restaurar o modo inválido anterior, pois isso poderia reabrir permissões e uma divergência de caminho torna incerto qual objeto seria alterado. Não criar recibo ou cópia dentro do diretório que está sendo corrigido.

5. **Exigir inventário separado depois do sucesso.** A operação encerra sem calcular ou emitir fingerprint de aprovação nova e sem encadear jobs. Um novo `support-inventory` read-only comprova `ready` e fornece a fingerprint atual. `prepare-support` continua sendo despacho separado, com sua própria revisão e autorização.

## Risks / Trade-offs

- **Mudança concorrente fora do lock comum** → comparar fingerprint antes da alteração, operar pelo descritor fixo e verificar identidade/estado depois; se a prova não fechar, parar sem novas tentativas.
- **Falha de verificação após `fchmod`** → não repetir a mutação; preservar o estado observado, emitir código sanitizado e exigir novo inventário/manual review antes de qualquer operação posterior.
- **Resumo revelar detalhes do host** → saída limitada a resultado/código allowlisted; não exibir caminho, modo observado, UID/GID, nomes, conteúdo ou exceção.
- **Teste local Windows não representar permissões POSIX** → cobrir contrato sintético e semântica de modo em runner Linux da CI; skips locais não serão contados como evidência dessa semântica.

## Migration Plan

1. Implementar e validar helper, workflow e testes sintéticos em branch/PR; revisar o diff e não despachar operação remota.
2. Revisar e integrar a PR; exigir CI verde da `main` no SHA exato.
3. Executar um novo `support-inventory` read-only e apresentar o inventário/fingerprint atuais. A fingerprint `5b4f5c1c…` de 24/11 é histórica e não aprova esta operação.
4. Somente após aprovação operacional da fingerprint atual e aprovação do ambiente `production`, despachar `repair-support-backups-mode` separadamente.
5. Após sucesso, despachar outro `support-inventory` read-only. Se o diretório estiver `ready`, a preparação de suporte ainda requer despacho/fingerprint/approval próprios; o inventário do runtime permanece uma etapa posterior e separada.

## Open Questions

Nenhuma. O escopo é deliberadamente limitado à correção de modo já especificada pelo contrato atual; as demais categorias não serão remediadas por esta change.
