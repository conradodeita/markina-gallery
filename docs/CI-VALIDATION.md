# Validação CI do backend

## Linha de base observada

Amostra de três execuções recentes da CI; não é suficiente para estimar p90. O tempo é o tempo de parede entre criação e atualização do workflow, sem subtrair fila.

| Run | CI total | Shard backend mais lento | `backend-quality` |
|---|---:|---:|---:|
| [44424649626](https://github.com/conradodeita/markina-gallery/actions/runs/44424649626) | 19m03s | 18m25s | 1m47s |
| [44428285088](https://github.com/conradodeita/markina-gallery/actions/runs/44428285088) | 26m52s | 26m27s | 2m18s |
| [44433195647](https://github.com/conradodeita/markina-gallery/actions/runs/44433195647) | 31m22s | 30m53s | 2m17s |

A mediana observada da CI nessa amostra é **26m52s**; a mediana do shard mais lento é **26m27s**. `backend-quality` levou entre 1m47s e 2m18s. No run 44433195647, o gate de qualidade falhou em `NoCopy volume check` após 2m17s, mas os três shards continuaram em paralelo e o workflow terminou 29m05s depois. A nova dependência faz os shards esperarem o gate de qualidade; a primeira medição no PR está registrada abaixo, mas são necessárias mais execuções verdes para avaliar ganho consistente.

Os três shards desse run passaram e produziram JUnit e manifestos compatíveis com SHA `feef56a9702c50bea500a511a7c457cbe4aba46b` (head do PR `9dba58e5e589d815762e663d83f92c2b41ba2103`). A amostra cobre **2.625 itens em 251 módulos**. Os tempos agregados do JUnit por distribuição anterior, em minutos de execução de casos, foram **29,786 / 18,407 / 19,733**.

Na configuração inicial, `scripts/backend_ci_durations.json` registrava os segundos por módulo da coleta única e fallback de **0,849 s por caso**. A projeção LPT daquela versão estimava **22,642 min de casos por shard**, contra **29,786 / 18,407 / 19,733 min** sob distribuição por quantidade. Esses valores são a linha de base histórica de uma coleta, não medição posterior nem tempo de parede.

## Primeira medição da otimização no PR

O primeiro run verde da versão otimizada foi o [44458427627](https://github.com/conradodeita/markina-gallery/actions/runs/44458427627), no SHA `e441a2582e8644de05234f601fd9afce872655ba`, em 19/11/2026.

| Resultado | CI total | Fila API | Shard 0 | Shard 1 | Shard 2 | Cobertura backend |
|---|---:|---:|---:|---:|---:|---:|
| sucesso | 26m46s | 0s* | 24m02s | 23m06s | 22m14s | 2.625/2.625, uma vez cada |

`backend-quality` levou 1m49s; frontend, 2m26s; imagem ARM64, 2m31s; imagem AMD64, 2m50s. O run levou 6 segundos menos que a mediana total histórica de 26m52s, diferença pequena demais para indicar ganho. O shard mais lento levou 2m25s menos que a mediana histórica de 26m27s, mas há apenas uma execução verde pós-mudança; p90 e redução estável do tempo total seguem sem amostra suficiente. *`created_at` e `run_started_at` do GitHub têm o mesmo segundo; o primeiro job iniciou 3 segundos depois.*

Os runs [44450998998](https://github.com/conradodeita/markina-gallery/actions/runs/44450998998) (27m02s) e [44454598575](https://github.com/conradodeita/markina-gallery/actions/runs/44454598575) (26m22s) falharam no contrato de política de release, não na suíte de produto: o primeiro expôs a classificação do histórico desde um baseline de produção antigo; a correção inicial passou a aceitar mudanças de app e foi corretamente rejeitada pela regressão de blob não revisado no segundo. A classificação foi então limitada às mudanças posteriores ao snapshot aprovado do manifesto, sem alterar o avaliador fail-closed. Na execução verde, os três shards, o agregado `backend`, `homolog-inventory-policy` e `gemma-runtime` passaram. Não houve cancelamentos; os jobs de release de produção foram ignorados por ser um evento de PR.

## Recalibração para quatro shards — projeção pendente de medição

Os runs [44433195647](https://github.com/conradodeita/markina-gallery/actions/runs/44433195647) e [44461878620](https://github.com/conradodeita/markina-gallery/actions/runs/44461878620) têm os mesmos **2.625 node IDs em 251 módulos** e JUnit válido; os shards passaram nos dois. A execução 444618 foi verde; 444331 falhou depois no gate `backend-quality`. A correlação das médias por módulo foi **0,957**. O perfil atualizado combina os tempos JUnit das duas amostras; os registros `items` contam observações (5.250 no total, duas por caso único), enquanto `source.collected_items` continua representando os 2.625 casos da coleção. O fallback pela mediana conjunta é **0,7845 s/caso**.

Mantendo módulos indivisíveis, o LPT de quatro shards projeta **15,90 min de carga por shard**; ao reaplicar a partição aos tempos de caso da amostra mais recente, o shard mais lento fica em **16,12 min**. Para comparação, a maior soma observada de tempos JUnit na distribuição anterior de três partes foi **23,80 min**. São projeções de duração de casos, não duração real de job ou workflow: o plano adiciona um runner e um par isolado de serviços PostgreSQL. Fila, inicialização, duração de parede, cobertura integral e custo serão medidos no primeiro CI desta matriz.

## Seleção e gates

- Todos os eventos que não sejam `pull_request`, incluindo push e `workflow_dispatch`, usam `--full`.
- Workflows, classificador, infraestrutura, runtime, segurança, dependências e caminhos desconhecidos continuam acionando os escopos completos.
- A única exceção inicial são `scripts/ci_feedback.py` e `scripts/test_ci_feedback.py`: a ferramenta read-only e seus testes rodam no gate de escopo; sozinhos, podem omitir somente a suíte de produto backend. O script operacional de deploy, seu harness de teste, qualquer outro `scripts/*` e combinações com runtime não estão allowlisted.
- `backend-quality` valida lint e contratos de scripts. `backend-tests` começa somente após sucesso desse gate; a matriz mantém quatro shards e `fail-fast: false` para coletar todos os diagnósticos de uma suíte que iniciou.
- O job agregado `backend` mantém o nome/status exigido. Só aceita `backend-tests: skipped` quando `ci-scope` marcou explicitamente `backend_tests=false`; caso contrário exige sucesso e verifica os quatro artefatos.
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

Os relatórios `backend-shard-0` a `backend-shard-3` preservam manifesto e JUnit por sete dias. Cada manifesto vincula o plano ao SHA e ao hash do perfil de duração; o verificador rejeita revisão divergente, perfil diferente, seleção alterada, shard ausente, falha, omissão ou sobreposição.

## Limites e trabalho restante

A seleção sem shards ainda é estreita: não há mapa abrangente de dependências entre módulos de runtime backend e testes. A fixture `autouse` em `backend/tests/conftest.py` restaura regras DDL sobre `Base.metadata` compartilhado; `test_derived_galleries.py` recria o schema global por caso e importa `app.main` e vários domínios; `test_unified_checkout.py` importa fixture do primeiro arquivo. Por isso, alterações de runtime backend continuam com a suíte completa. A próxima redução exige mapa de impacto comprovado e comparação com full CI antes de ser ativada. A recalibração de pesos usa duas execuções comparáveis, ainda uma amostra pequena; novas amostras bem-sucedidas poderão orientar ajustes. P90, tempo em fila, consumo faturado de runners e ganho real das mudanças ainda aguardam amostra pós-mudança.

A falha `NoCopy volume check` do run 44433195647 pertence à branch de release bridge e continua independente desta otimização. Nenhuma etapa desta change acessa servidor, secrets, dados de produção, executa migration, deploy ou alteração externa do GitHub.
