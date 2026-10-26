# Validação CI do backend

A suíte completa permanece obrigatória em pushes protegidos e operações manuais. Em PRs, o classificador existente seleciona as áreas afetadas; workflows, scripts, infraestrutura ou caminhos desconhecidos continuam acionando toda a matriz.

## Execução

- `backend-quality`: lint e testes de políticas/scripts, uma única execução.
- `backend-tests (0/1/2)`: três runners independentes, cada um com SQLite e dois serviços PostgreSQL descartáveis próprios. Cada runner coleta todos os testes, mas executa somente sua parte; módulos e sua ordem interna permanecem juntos. A carga é balanceada por quantidade de itens coletados.
- `backend`: exige sucesso de qualidade e de todas as partes e verifica os manifestos. Coleção divergente, parte ausente, cancelada ou falha, seleção incompleta e sobreposição impedem aprovação. Os jobs de release continuam dependendo desse mesmo nome.

Os testes de concorrência já usam PHOTOGRAPHER_TEST_DATABASE_URL no ambiente da suíte completa. Os passos focados redundantes foram removidos. A variante de exclusão em PostgreSQL continua executando na parte 0 com DATABASE_URL explícita; a execução do mesmo contrato em SQLite também permanece na suíte geral.

## Evidência e diagnóstico

Os artefatos `backend-shard-0`, `backend-shard-1` e `backend-shard-2` contêm manifesto JSON e JUnit XML, com retenção de sete dias. O manifesto inclui SHA, índice, coleção completa, seleção e exit code do pytest. Os logs mostram os 25 testes mais lentos de cada parte. Os artefatos não contêm dados de produção.

Baseline observado em 26/10/2026: [run 40397675011](https://github.com/conradodeita/markina-gallery/actions/runs/40397675011), SHA 455afaaacb0199da48588dea3ffc0a2b53d03761: backend 32min; passo pytest 27min41s; 1577 passed e 23 skipped. Seis passos focados repetiam cerca de 2min23s; concorrência posterior repetia mais 13s. A regressão de exclusão de 4s é preservada porque a configuração difere.

A redução real de tempo de parede deve ser medida no CI da PR, incluindo filas, preparação e agregação. A distribuição aumenta o número de runners simultâneos e pode aumentar overhead faturado; não promete redução de minutos faturados. Se um módulo dominar uma parte, usar os novos tempos para analisar sua fixture, sem excluir testes ou reduzir assertions automaticamente.

## Reprodução local

Em ambiente sintético com dependências e bancos de teste preparados:

```sh
python scripts/backend_ci.py run --index 0 --count 3 --output /tmp/backend-reports/shard-0.json
```

Executar as outras partes em ambientes/bancos separados. Não executar as três partes simultaneamente contra os mesmos bancos. Reunir seus manifestos e conferir:

```sh
python scripts/backend_ci.py verify --count 3 --artifacts /tmp/backend-reports
python -m unittest scripts.test_backend_ci scripts.test_check_ci_results scripts.test_classify_ci_scope -v
```

Sem GITHUB_SHA, os manifestos usam a revisão `local`. Um erro de coleta/teste produz saída não zero; nenhum status anterior pode substituir esse resultado. Cancelamento também é bloqueado pelo resultado do job, mesmo que já exista manifesto.

## Recuperação e release

Se a distribuição expuser dependências entre módulos ou regressões do workflow, corrigir em PR; reverter a otimização restaura a suíte serial. A mudança não edita testes do produto, chaves, gates de aprovação, migrations nem scripts de deploy. Não cancela runs antigos e não encurta retroativamente uma execução já iniciada. Integração deve ser coordenada com o SHA de suporte/fingerprint de qualquer release em andamento.
