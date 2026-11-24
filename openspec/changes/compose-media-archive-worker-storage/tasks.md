# Tasks

## 1. Revisão arquitetural antes do código

- [x] 1.1 Reconciliar a identidade Workspace dedicada distinta do backup e raiz própria já aprovadas; documentar injeção sintética e deixar provisão/custódia/OAuth real no gate 1.4; validar consistência com `openspec validate compose-media-archive-worker-storage --strict`.
- [x] 1.2 Revisar consumidores de `media_archive_worker.claim_next_operation`, confirmar filtro opcional por tenant isolado e registrar o tratamento de job/lease global pertencente a outro tenant; comprovar por mapa de chamadas que `gallery_lifecycle.claim_next_operation` e o fluxo de backup não entram no delta.

## 2. Composição explícita e isolamento do piloto

- [x] 2.1 Implementar binding somente para invocação direta do harness sintético local, mantendo o loop sem argumento fechado e recusando registro de storage volátil e validando tenant, raiz/namespace e staging antes de descoberta/claim; testes de configuração ausente, gate fechado e divergência devem provar zero mutações de fila/lease, zero chamadas ao transporte e erros/logs sanitizados.
- [x] 2.2 Restringir claims novos e retomadas de lease ao tenant do proprietário antes de executar o adapter; preservar o coordenador global e estados de outros tenants. Testes sintéticos devem provar que jobs de terceiros permanecem inalterados e que lease global de outro tenant não é retomado, liberado ou transferido.
- [x] 2.3 Compor o adapter com o dispatcher/executor existente usando transporte e dados sintéticos, provando arquivo, readback e recuperação íntegros; registrar a decisão aprovada, limites e evidências em `design.md`, no runbook de arquivo/backup e na validação da change.

## 3. Integração e revisão local

- [x] 3.1 Executar testes focados do dispatcher, claim/lease, adapter e executor; executar `backend/tests/test_platform_backup_workspace_store.py` sem alterar os arquivos de backup e registrar resultados/limites.
- [x] 3.2 Executar Ruff nos arquivos afetados, `openspec validate compose-media-archive-worker-storage --strict`, `git diff --check` e revisão final de escopo/segredos/compatibilidade; registrar comandos, skips, ambiente e hashes relevantes nos artefatos OpenSpec.

## Workflow follow-up

- Retomar a task operacional 1.4 somente após implementação/revisão desta change, backup global comprovado, release/ambiente autorizado e prova independente do vínculo OAuth de mídia, raiz, permissões e limites. O primeiro ensaio futuro permanece restrito ao tenant/galeria sintética do proprietário.
- Não usar `Oracle Production Ensaios` para clientes, backup global ou dados reais; não liberar outros tenants até o ensaio autorizado e a recuperação completa passarem.
- Antes de qualquer expansão multi-tenant, resolver o modelo indicado em `design.md` e criar/revisar os gates correspondentes; esta proposta não autoriza ativação, Drive real, host, deploy ou alteração de produção.

## Evidência do checkpoint local

Tasks locais validadas em `validation.md` em 24/11/2026. A conclusão desta checklist não conclui a task operacional 1.4, não autentica proprietário/identidade real e não libera Drive ou outros tenants. Os quatro casos PostgreSQL anteriormente ignorados foram executados em container exclusivo descartável: 29 testes aprovados, zero skips nos módulos de claim/scheduler, incluindo novas provas tenant/lease concorrentes. Evidências e limpeza em `validation.md`.

A revisão corretiva da task 2.1 fechou totalmente a configuração do loop, inclusive para storage em memória; fixtures só entram pelo harness direto local. Em production também a injeção direta é recusada. Evidência atual em `validation.md`.
