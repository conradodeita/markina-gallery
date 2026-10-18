# Tasks

## 1. Documentar e reconciliar a base

- [x] 1.1 Registrar SHA observado, revisão Alembic e política atual do ambiente, sem expor segredos ou dados identificáveis. Evidência: inventário `39036197944`; revisão `0779b3e`, Alembic `20261016_0082`, homolog restrita a branches protegidas e reviewer obrigatório.
- [x] 1.2 Integrar `main` em `develop` por PR, preservando a change de produto e resolvendo conflitos com base nos contratos e no código atual. PR #210 integrada no commit `c9eaf638`, com os seis checks requeridos aprovados.

## 2. Corrigir o grafo de migrations

- [x] 2.1 Renumerar a migration de escopo privado como revisão única imediatamente após `20261016_0082`. Arquivo `20261017_0083_private_upload_batch_folder_scope.py`, revisão e `down_revision` conferidos no código integrado.
- [x] 2.2 Atualizar regressões para migrar de `20261016_0082` à nova head e verificar constraints/colunas. `test_private_upload_batch_scope_migration_preserves_legacy_schema` percorre 0081 → 0082 → 0083 e verifica colunas, FKs, check de escopo e remoção da unicidade global de ativo; integra o backend aprovado do CI `39046656588`, com PostgreSQL sintético configurado. O deploy também confirmou a atualização efetiva 0082 → 0083.
- [x] 2.3 Executar os testes focados e validação OpenSpec estrita; registrar hashes e resultados verificáveis. Evidências locais anteriores e CI integral do alvo `25cd338` em `validation.md`; backend `1650 passed, 23 skipped`, checks obrigatórios verdes.
- [x] 2.4 Restringir o teste de blobs do release facial a PRs/pushes de `main`, mantendo a validação de homologação em `develop`; proteger essa condição com teste de política e sem alterar `production-gates.json`. Checks da PR #210 e política de homologação do CI `39046656588` aprovados; nenhum gate de produção foi liberado por esta change.

## 3. Publicar com escopo controlado

- [x] 3.1 Proteger `develop` com os mesmos checks requeridos em `main`, sem force-push/deleção e com enforcement ativo; isso torna a branch elegível sob a política existente `protected_branches=true`. Reviewer obrigatório do ambiente `homolog` permanece ativo. Nenhuma regra de produção foi modificada.
- [x] 3.2 Confirmar inventário e plano de impacto zero com o alvo reconciliado antes de aprovar o job de deploy. Registrados no chat executor anterior e no fluxo protegido `39046656588`: projeto exclusivo `markina-gallery`, entrada `127.0.0.1:8080`, domínio `markina.pickyourpic.com.br`, backup e intervenção restrita à Markina. A correção intermediária do probe está na change `fix-homolog-deploy-stale-revision-probe`/PR #212.
- [x] 3.3 Após o deploy, confirmar SHA, revisão Alembic, health checks e saúde dos serviços do projeto `markina-gallery`. Deploy `39046656588` aprovado; inventário `39049112709` confirmou `25cd338`, revisão `20261017_0083`, serviços saudáveis e HTTP 200 em `/healthz` e `/api/health`. Conferência somente leitura do chat sucessor em 17/10/2026 confirmou checkout limpo, mesmo SHA e serviços saudáveis.

## Revisão final

- As tarefas de implementação, integração e publicação estão concluídas com evidência. Sincronização das specs principais e arquivamento continuam condicionados à revisão humana; esta reconciliação documental não os executa nem autoriza novo deploy.
