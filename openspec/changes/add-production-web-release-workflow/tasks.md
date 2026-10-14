## 1. Procedimento e automação de release

- [x] 1.1 Implementar fase somente-leitura de inventário em `scripts/deploy-prod-web.sh`, verificando raiz, branch/SHA, serviços Compose, portas, domínio e arquivo de ambiente montado sem exibir valores; validar com testes de shell que divergências abortam antes de mutações. Evidência: inventário SSH somente-leitura em 2026-10-14 confirmou projeto, portas, domínio, `.env.homolog` ignorado pelo Git e hash do web igual a `docker compose config --hash web`; teste simulado recusa hash divergente antes de qualquer mutação.
- [x] 1.2 Implementar execução aprovada e rollback restritos ao serviço `web`, sem dependências, migrations ou alterações de configuração; validar por testes que comandos de mutação selecionam somente `web` e que entradas inválidas são recusadas. Evidência: `bash scripts/test_deploy_prod_web.sh` verifica comandos web-only e recusa código de aprovação divergente sem mutação.
- [x] 1.3 Documentar em `docs/DEPLOY-PROD-WEB.md` inventário, aprovação por execução, domínio/portas, possível interrupção, smoke tests, registro de SHAs e rollback; conferir que o runbook não reutiliza o fluxo de homologação. Evidência: revisão do runbook inclui manifesto Compose observado e não aciona o job de homologação.

## 2. Validação e revisão operacional

- [x] 2.1 Executar testes do script, validação OpenSpec e revisão do diff para confirmar que somente automação/documentação especificadas foram alteradas e que nenhum segredo foi exposto. Evidência: Bash sintático válido no Git Bash; testes shell/policy e `openspec validate --strict` passaram; diff focado revisado.
- [x] 2.2 Apresentar inventário atualizado e plano de impacto do host real ao proprietário; confirmar que qualquer release permanece condicionado a aprovação explícita por execução. Evidência: inventário remoto somente-leitura confirmou produção em `132.145.193.169`, domínio `markina.pickyourpic.com.br`, proxy local `127.0.0.1:8080` e serviço `web` interno na porta 3000; SHA ativo `aa7119c0b82bd5fa147fe6bbdac98dfa21091190`; nenhum release executado. Rechecagem em 2026-10-14 confirmou checkout remoto limpo e que o gate local requer SHA de `origin/main` (`e0b29dd…`), cuja árvore `frontend` contém apenas o esqueleto de health/layout e não contém o app de galeria. `origin/develop` está 562 commits à frente e 11 atrás de `main`, com diferença em 1.524 arquivos; o SHA ativo é ancestral de `develop`. Não existe ainda SHA candidato aprovável; o gate não foi contornado e uma sincronização integral não foi autorizada.


## 3. Integração autorizada para revisão

- [x] 3.1 Preparar branch isolada a partir de `aa7119c`, incorporar `main` preservando o histórico e os contratos de manutenção/inventário; verificar que a aplicação e Compose ainda são idênticos ao SHA ativo antes da otimização.
- [x] 3.2 Portar o procedimento e validar scripts, políticas, OpenSpec e CI na árvore integrada; registrar limitações concretas.
- [x] 3.3 Publicar PR em draft para main com comparação explícita contra a produção, sem merge/deploy.

A decisão posterior do proprietário autoriza a preparação descrita em `integration.md`; substitui o bloqueio anterior de autorização para preparar a reconciliação. Merge, revisão humana e release permanecem gates separados.


Evidência da preparação em 2026-10-14: merge local `a2523eb` conserva os pais `aa7119c` e `e0b29dd`. Antes da correção, `git diff --cached --name-only -- frontend backend docker` ficou vazio. Testes de política do inventário (3), de manutenção e do procedimento web passaram; o script recusa portas/configuração/aprovação divergentes. O procedimento também valida host, origin exato e igualdade de `docker/` antes de trocar checkout. `@fission-ai/openspec@1.14.0` (versão do CI) validou todos os 101 itens. A execução por `@latest` não representa o contrato do CI e produziu os mesmos 29 avisos em candidata e baseline; nenhuma alteração em specs alheias foi necessária.


PR draft criado: https://github.com/conradodeita/markina-gallery/pull/179, branch `feature/production-gallery-integration`, alvo `main`. Correção de produto no commit `6e32486ccbb960971b60ccc79029cf09deecabcc`; procedimento em `8c15647`; integração em `a2523eb`. Os checks do SHA corrente são registrados pelo GitHub no PR, com backend, frontend, OpenSpec, gitleaks, política de inventário e runtime Gemma. Abertura do PR não executa deploy: o job de deploy exige push em develop. Merge/release não foram executados nesta preparação.
