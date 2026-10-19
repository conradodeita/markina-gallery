# Tasks

## 1. Corrigir e proteger a configuração

- [x] 1.1 Trocar somente o ecossistema de `/docker` para `docker-compose`; preservar Docker backend/frontend, limite, agenda, grupos e ausência de automerge.
- [x] 1.2 Adicionar regressão que assegure a entrada correta e a cobertura dos cinco manifests Compose base/overlays encontrados no repositório.
- [x] 1.3 Executar os testes direcionados, validar o OpenSpec e rever o diff para confirmar ausência de mudanças em versões, imagens, serviços ou deploy (9 testes do relatório passaram; `openspec validate fix-dependabot-compose-ecosystem --strict` passou; `git diff --check` passou; diff limitado à configuração, teste e artifacts OpenSpec).

## 2. Validar e integrar

- [x] 2.1 Abrir PR #247 para `main`; a checagem GitHub `.github/dependabot.yml` passou, todos os checks obrigatórios passaram no run `39328116406` e a proteção exigia os seis contextos existentes, sem aprovação extra.
- [x] 2.2 Execução real `docker_compose in /docker` passou no run Dependabot `39332850554` (job 118335027393, 43s) e gerou PR #248 apenas para `docker/docker-compose.yml`; PR de dependência permaneceu aberta e sem merge.
- [x] 2.3 PR #247 integrada após checks verdes; o classificador retornou `release_scope=none`, e jobs de deploy/preflight/release permaneceram skipped. Nenhum deploy, serviço ou recurso Oracle foi acessado.
