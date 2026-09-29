# Tasks

## 1. Caminho seguro de retomada

- [x] 1.1 Implementar o procedimento versionado de retomada para iniciar somente os contêineres de aplicação existentes, sem dependências, recriação ou migration; adicionar testes que confirmem argumento `--no-deps`/`--no-recreate`, lista delimitada de serviços e ausência de invocação Alembic/`migrate`. Evidência: `bash -n scripts/resume-homolog.sh` (Git Bash) e `python scripts/test_resume_homolog_policy.py` aprovados em 2026-09-29.
- [x] 1.2 Implementar preflight e verificação posterior de DB/Redis/revisão, healthchecks e endpoints; testar indisponibilidade, divergência de revisão, workers opcionais e ausência de serviço, assegurando falha fechada sem comandos destrutivos. Evidência: `bash scripts/test_resume_homolog.sh` (stubs de Compose/Docker/HTTP), `python scripts/test_assert_homolog_schema_head.py -v` (4 casos) e comparação do head real com `20260929_0069` aprovados em 2026-09-29.
- [x] 1.3 Atualizar documentação operacional para distinguir retomada simples de deploy com migration; verificar cada comando documentado contra o procedimento automatizado e registrar restrições do ambiente compartilhado. Evidência: `python scripts/test_resume_homolog_policy.py` confere o comando documentado, as flags e exclusões de migration/Evolution/projetos vizinhos.

## 2. Validação integrada

- [x] 2.1 Executar testes de política do deploy, sintaxe e validação OpenSpec estrita completa; registrar comandos e resultados verificáveis. Evidência: `scripts/test_deploy_homolog.sh` e política do deploy aprovados; testes `resume-homolog` aprovados; três scripts passam `bash -n`; Ruff dos auxiliares Python aprovado; `openspec validate --strict --all --no-interactive` passou com 72/72 itens em 2026-09-29.
- [ ] 2.2 Apresentar inventário remoto somente-leitura, portas/subdomínio e plano de impacto zero antes de qualquer ensaio em homologação; aguardar autorização operacional específica e então verificar retomada, revisão inalterada, endpoints, Evolution e serviços vizinhos, ou registrar a task como bloqueada sem alegar validação remota.

Inventário somente-leitura e plano do ensaio registrados em `validation.md` em 2026-09-29. Nenhuma alteração remota foi feita; a retomada real depende de publicar esta change pelo fluxo aprovado e receber autorização específica para a janela de teste.
