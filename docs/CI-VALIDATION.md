# Validação CI do backend

## Linha de base observada

Amostra de três execuções recentes da CI; não é suficiente para estimar p90. O tempo é o tempo de parede entre criação e atualização do workflow, sem subtrair fila.

| Run | CI total | Shard backend mais lento | `backend-quality` |
|---|---:|---:|---:|
| [44424649626](https://github.com/conradodeita/markina-gallery/actions/runs/44424649626) | 19m03s | 18m25s | 1m47s |
| [44428285088](https://github.com/conradodeita/markina-gallery/actions/runs/44428285088) | 26m52s | 26m27s | 2m18s |
| [44433195647](https://github.com/conradodeita/markina-gallery/actions/runs/44433195647) | 31m22s | 30m53s | 2m17s |

A mediana observada da CI nessa amostra é **26m52s**; a mediana do shard mais lento é **26m27s**. `backend-quality` levou entre 1m47s e 2m18s. No run 44433195647, o gate de qualidade falhou em `NoCopy volume check` após 2m17s, mas os três shards continuaram em paralelo e o workflow terminou 29m05s depois. A nova dependência faz os shards esperarem o gate de qualidade; a economia real ainda depende de uma execução após o merge.

Os três shards desse run passaram e produziram JUnit e manifestos compatíveis com SHA `feef56a9702c50bea500a511a7c457cbe4aba46b` (head do PR `9dba58e5e589d815762e663d83f92c2b41ba2103`). A amostra cobre **2.625 itens em 251 módulos**. Os tempos agregados do JUnit por distribuição anterior, em minutos de execução de casos, foram **29,786 / 18,407 / 19,733**.

O arquivo `scripts/backend_ci_durations.json` registra os segundos observados por módulo, o run de origem, os dois SHAs e a mediana de **0,849 s por caso** usada como fallback. Uma projeção LPT offline, mantendo módulos inteiros, estima **22,642 min de casos por shard**. A distribuição atual por quantidade estima **29,786 / 18,407 / 19,733 min** sob os mesmos pesos. Essa é uma projeção de uma única coleta, não uma medição posterior à mudança, nem uma promessa sobre o tempo total de parede.

## Seleção e gates

- Todos os eventos que não sejam `pull_request`, incluindo push e `workflow_dispatch`, usam `--full`.
- Workflows, classificador, infraestrutura, runtime, segurança, dependências e caminhos desconhecidos continuam acionando os escopos completos.
- A única exceção inicial são `scripts/ci_feedback.py` e `scripts/test_ci_feedback.py`: a ferramenta read-only e seus testes rodam no gate de escopo; sozinhos, podem omitir somente a suíte de produto backend. O script operacional de deploy, seu harness de teste, qualquer outro `scripts/*` e combinações com runtime não estão allowlisted.
- `backend-quality` valida lint e contratos de scripts. `backend-tests` começa somente após sucesso desse gate; a matriz mantém três shards e `fail-fast: false` para coletar todos os diagnósticos de uma suíte que iniciou.
- O job agregado `backend` mantém o nome/status exigido. Só aceita `backend-tests: skipped` quando `ci-scope` marcou explicitamente `backend_tests=false`; caso contrário exige sucesso e verifica os três artefatos.
- O agregador `homolog-inventory-policy` conserva o ID de check exigido pela configuração existente, mas não acessa homologação. Um teste impede que workflows, environments ou secrets SSH desse alvo retornem.

## Cancelamento e caches

A concorrência usa o número do PR e permite cancelamento somente para `pull_request`. Pushes e `workflow_dispatch` usam `run_id` único e `cancel-in-progress=false` implicitamente, então uma nova execução não cancela release ou operação protegida. Nenhuma proteção externa do GitHub foi alterada.

`setup-python` já usa cache pip por arquivos de dependências e `setup-node` cache npm por `package-lock.json`. A matriz de imagens não configura cache BuildKit/GitHub Actions; a change não introduz cache Docker sem demonstração de ganho e isolamento seguro entre PRs não confiáveis.

## Reproduzir os contratos localmente

Antes do push, `python scripts/ci_local.py --base origin/main` detecta diferenças entre a base e `HEAD`, mudanças staged/unstaged e arquivos não rastreados. Executa somente os lints e contratos rápidos conhecidos e lista os gates completos que continuam obrigatórios no CI. Para inspecionar sem executar, acrescente `--dry-run`; para comprovar a seleção, use `--paths <arquivo> ...`. Um lint local não substitui suíte de produto, builds, Gitleaks ou CI do SHA.

```sh
python -m unittest scripts.test_classify_ci_scope scripts.test_backend_ci \
  scripts.test_check_backend_ci_results scripts.test_check_ci_results \
  scripts.test_ci_workflow_policy scripts.test_ci_feedback scripts.test_ci_local -v
ruff check scripts/backend_ci.py scripts/test_backend_ci.py \
  scripts/classify_ci_scope.py scripts/test_classify_ci_scope.py \
  scripts/check_backend_ci_results.py scripts/test_check_backend_ci_results.py \
  scripts/ci_feedback.py scripts/test_ci_feedback.py scripts/test_ci_local.py \
  scripts/ci_local.py scripts/test_ci_workflow_policy.py
npx -y @fission-ai/openspec@1.14.0 validate optimize-ci-feedback-cycle --strict --no-interactive
```

Os relatórios `backend-shard-0`, `backend-shard-1` e `backend-shard-2` preservam manifesto e JUnit por sete dias. Cada manifesto vincula o plano ao SHA e ao hash do perfil de duração; o verificador rejeita revisão divergente, perfil diferente, seleção alterada, shard ausente, falha, omissão ou sobreposição.

## Limites e trabalho restante

A seleção sem shards ainda é estreita: não há mapa abrangente de dependências entre módulos de runtime backend e testes. A fixture `autouse` em `backend/tests/conftest.py` restaura regras DDL sobre `Base.metadata` compartilhado; `test_derived_galleries.py` recria o schema global por caso e importa `app.main` e vários domínios; `test_unified_checkout.py` importa fixture do primeiro arquivo. Por isso, alterações de runtime backend continuam com a suíte completa. A próxima redução exige mapa de impacto comprovado e comparação com full CI antes de ser ativada. Os pesos vieram de uma execução; coletar novos JUnit bem-sucedidos e recalibrar somente com evidência. P90, tempo em fila, consumo faturado de runners e ganho real das mudanças ainda aguardam amostra pós-merge.

A falha `NoCopy volume check` do run 44433195647 pertence à branch de release bridge e continua independente desta otimização. Nenhuma etapa desta change acessa servidor, secrets, dados de produção, executa migration, deploy ou alteração externa do GitHub.
