# Correção pontual do snapshot — evidências

## Escopo e autorização

Branch codex/fix-snapshot-optional-health-2026-10-18 baseada na main 34d2afd5b8f407adb70b0dee165fa8d55a83b478. Autorização: engenharia, testes, PR/CI e integração segura; nenhuma escrita Oracle para novo SHA. Registros anteriores preservados nas branches locais originais; o fechamento operacional foi consolidado no [registro da publicação](../remediate-frontend-dependency-vulnerabilities/production-publication-2026-10-19.md).

## Reprodução e correção

Docker CLI real contra API sintética em 127.0.0.1; Bash executa release_non_web_snapshot real. Não acessa daemon real nem cria containers. Antes: test_real_formatter_preserves_exited_and_optional_health falhou com a mesma mensagem da Oracle, template .State.Health: map has no entry for key Health. O teste de falha de inspect já passou. Depois: três regressões passaram em 7,211 s no host Windows com Docker CLI real.

Fixtures cobrem migrate exited sem Health, running sem healthcheck, Health vazio/null, Status ausente/null/vazio e healthy/unhealthy/starting. Esperado inclui todos os não-web, inclusive parados; web permanece excluído. Requests somente GET, all=1 obrigatório. Falha de inspect e ausência de StartedAt obrigatório continuam falhando. Leitura opcional usa with/index em uma única linha; pins state atualizados em web/app e pin app no wrapper acompanha o conteúdo. Nenhum gate, allowlist, lock, alvo/escopo ou configuração foi relaxado.

## Code Review e verificação dos apontamentos

Code Review local somente leitura foi executado sobre o diff e levantou duas hipóteses, investigadas com evidência:

1. Alegou que State é necessariamente struct e index falharia. Não corresponde ao contrato observado: o erro real da Oracle já identifica map e a regressão usa o formatador do Docker CLI, não uma imitação Python do template, passando com JSON sem Health. O CI Linux posteriormente executou o cliente real com sucesso; resultados definitivos abaixo. Não substituir por acesso direto que reproduz o defeito comprovado.
2. Alegou ausência de execução no CI. Cadeia existente: .github/workflows/ci.yml, passo Persistência de branding e política de deploy, chama bash scripts/test_deploy_prod_web.sh, que chama python3 scripts/test_prod_release_state.py sem seleção; unittest.main descobre DockerSnapshotContracts. Nenhum workflow novo é necessário. Ausência de Docker CLI em CI causa falha explícita; apenas ambiente local sem cliente pode registrar skip, separado da execução real Windows/Linux CI.

O revisor não substitui as evidências executáveis. Resultados definitivos dos contratos, CI e integração estão registrados ao final deste documento.

## Fechamento operacional

O runbook `docs/DEPLOY-PROD-WEB.md` foi executado após autorização específica para o SHA final de #228. Publicação concluída em 19/10/2026, sem migrations, limpeza ou remoção do migrate histórico. Ver [registro da publicação](../remediate-frontend-dependency-vulnerabilities/production-publication-2026-10-19.md). Esta consolidação não executa nova operação remota.

## Validação local final

32 contratos Linux aprovados em 77,637 s, zero skips, em contêiner local isolado sem rede/raiz gravável, fontes read-only, 512 MiB/2 CPUs. Separadamente três testes com Docker CLI real 29.8.2 e API sintética passaram, incluindo propagação de erro e recusa de campo obrigatório ausente. 11 testes de escopo app e 12 de classificação passaram; políticas web/workflows, Ruff, Bash syntax e diff-check passaram. OpenSpec CLI 1.14.0 --strict --all aprovado. Nenhuma escrita Oracle executada nesta retomada.

Proteções main consultadas: seis checks estritos, enforce_admins true, zero aprovações formais exigidas; zero hooks/rulesets adicionais. Workflows inalterados: CI PR/push, homolog somente develop, operações main condicionadas ao classificador; demais workflows manuais. Classificação confirmada antes do push/merge e no CI pós-merge: release_scope=none; nenhuma revisão foi contornada.

## Resultado definitivo do CI e revisão

O CI do PR #228 (39183663312) confirmou os três testes reais do formatador e 35 contratos aprovados em 33,805 s. Backend geral: 1709 passed, 23 skipped, 658 warnings em 1844,61 s. Todos os seis checks obrigatórios aprovados. Segundo Code Review local, --base origin/main antes do merge: código 0, sem defeitos acionáveis.

Merge em 4b464f081dfa2451472848622853460398834e6d, às 2026-10-19T01:43:48Z, árvore idêntica ao head ca606b0e654e8dae124c54cc37a3f03a21ec229a. CI pós-merge 39186678648 completed/success: 35 contratos em 31,504 s; backend 1709 passed, 23 skipped, 658 warnings em 1740,25 s. release_scope=none, sete jobs de ambiente ignorados e zero deployments GitHub para o SHA. Registro completo em optional-health-integration.md; a publicação Oracle foi autorizada e concluída conforme registro operacional vinculado acima.
