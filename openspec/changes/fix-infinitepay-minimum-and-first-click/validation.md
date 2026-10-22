# Validation

## Estado inicial — 21/10/2026

Base publicada e CI anterior confirmados pelo proprietário: `21b89c3`, CI #776. Evidência local: `prepare_provider_payment` permite total positivo menor que 100 antes de reservar; `prepareCard` guarda o resultado e mostra outro link sem navegação. Testes anteriores verificam esse link, sem afirmar redirecionamento no primeiro clique.

As fontes e a lacuna do mínimo do Checkout Integrado estão em `design.md`. Não foi criada compra real, chamada InfinitePay ou alteração Oracle nesta investigação. PR #262 e PR #261 excluídos do diff.

## Resultados

### Guarda backend

`APP_ENV=test PYTHONPATH=backend DATABASE_URL=<PostgreSQL sintético local 127.0.0.1:15470/pyp_photographer_test> python -m pytest backend/tests/test_provider_checkout.py -k 'abaixo_de_um_real or total_minimo or tentativa_historica' -q --tb=short`: **5 passed, 26 deselected, 6 warnings, 41,00 s** após a guarda.

Antes da correção, os dois casos de R$ 0,05/R$ 0,99 falharam com **DID NOT RAISE HTTPException** (19,72 s), demonstrando emissão aceita pela fronteira sintética. Uma primeira execução tinha origem pública ausente na fixture (2 falhas/3 passes); a fixture foi corrigida antes de comprovar a regressão, sem alteração de runtime. Os cenários finais verificam ausência de ProviderPayment/Attempt, mesmas seleções/pedidos, PIX inalterado e reutilizável, total de 100/101 com itens de 1 centavo e repetição histórica sem nova reserva.

PostgreSQL local isolado já existente da missão #262, sem dados reais; sua execução anterior terminou com 77 testes aprovados antes desta suíte. Nenhum segredo operacional utilizado.

### Orientação no carrinho

`npm test -- app/library/cart/cart.test.tsx -t 'mínimo de um real|total exato de um real'`: antes da UI, **2 failed / 1 passed / 26 skipped**, pela ausência da orientação; após a UI, **3 passed / 26 skipped**, 3,47 s. As mesmas fotos e os dois links para continuar escolhendo permanecem, o cartão fica desabilitado abaixo de 100 e o PIX permanece utilizável; no total exato de 100 o cartão não é bloqueado.

### Primeiro clique

A regressão no teste existente `prepara uma única tentativa` falhou antes da navegação: **0 chamadas** ao adaptador de navegação (1 failed/28 skipped, 2,18 s). Após a correção, o arquivo do carrinho passou com **43 testes**, 4,72 s, incluindo duplo clique com resposta retida, oito URLs inválidas, cinco estados não navegáveis, ausência de navegação no GET/foco e erro de rede com idempotência preservada. Posteriormente acrescentados testes do adaptador de mesma aba e de falha de navegação; sua validação ampliada será registrada abaixo.

### Gate operacional — recusa inicial antes da preparação

`python scripts/test_production_release_workflow_policy.py` recusa a árvore modificada na linha 156: **arquivo de runtime app diverge do blob revisado**. Os manifests continuam descrevendo o runtime publicado e não autorizam estes novos blobs/arquivo de navegação. Não foram alterados allowlists, pins, wrappers ou scripts operacionais para forçar aprovação. Preparação de um novo candidato publicável requer revisão e atualização explícita do manifesto exato, com autorização própria; isso não impede validar funcionalmente a correção ou apresentar o PR em draft, mas impede declarar CI/release aprovados.

### Preparação exata para revisão após pedido de conclusão do roadmap

O checkpoint anterior foi superado por preparação local revisável, prevista no design/task4.0 antes do código: baseline21b89c3 já publicado e três blobs exatos da correção, com novo adaptador/teste de navegação nominados, sem wildcard. Não houve alteração dos mecanismos de autorização, fingerprint, migration, pins de dependências ou imagem base. A asserção do baseline no teste de política continua exata, atualizada para21b89c3; não foi removida. Cofre/migration0085 continuam recusados e excluídos.

- `python scripts/test_production_release_workflow_policy.py`: **production release workflow policy: ok**.
- `python -m unittest discover -s scripts -p test_prod_app_release_scope.py`: **18 testes aprovados**,128,929s, incluindo blob adulterado e arquivo semelhante não listado recusados.
- `python -m unittest discover -s scripts -p test_classify_prod_release.py`: **14 testes aprovados**,4,344s.
- `python scripts/check_prod_app_release_scope.py --base 21b89c332c6937b7079679888d52bd6a8aefe25d --target a4b950a`: **app_release_ready=true / somente_api_web**, usando o manifesto preparado localmente. O commit completo e o classificador real serão verificados antes de enviar o PR.
- Ruff dos arquivos backend e scripts alterados e `git diff --check`: aprovados.

Esses resultados não autorizam merge/deploy nem comprovam inventário, aprovação do novo candidato ou imagens em produção. A revisão do PR inclui o manifesto; autorização operacional continua etapa separada.

### Gates ampliados executados

- `npm test -- --maxWorkers=2`: **67 arquivos / 605 testes aprovados**, 173,57 s. Inclui teste do adaptador `location.assign` sem popup e preservação do link/reserva se a navegação falhar.
- A primeira suíte frontend padrão, em paralelo com build/lint, terminou com **600 passed / 5 failed**, todos os cinco por timeout de 5 s em arquivos administrativos não alterados. Memória livre observada em cerca de 850 MB. Repetição integral com dois workers, sem build concorrente, passou sem aumentar timeouts ou alterar esses testes/configuração.
- `npm run lint`: **0 erros / 34 avisos preexistentes**, exit0.
- `npm run build`: **exit0**, compilação, TypeScript e geração de páginas concluídos.
- `python -m ruff check backend/app/provider_checkout.py backend/tests/test_provider_checkout.py`: aprovado.
- `npx -y @fission-ai/openspec@1.14.0 validate --strict --all`: **133 passed / 0 failed**, versão exata do CI. A CLI global local 1.14.1 teve 30 recusas por novas verificações em changes anteriores; nenhuma spec não relacionada foi alterada para contorná-las.
- `git diff --check`: aprovado. Revisão proporcional: reaproveitados mutex, idempotência, projeção e reservas; link de retomada continua necessário como fallback e para compras já emitidas. Nenhuma remoção extra ou refatoração ampla é elegível.
- Matriz ampliada PostgreSQL concluída: `python -u -m pytest backend/tests/test_provider_checkout.py backend/tests/test_provider_cart_recovery.py backend/tests/test_provider_cart_recovery_api.py backend/tests/test_payment_provider.py -v --tb=short` com ambiente sintético local: **91 passed, 6 warnings,804,53s**. Inclui concorrência, confirmação antes da URL, respostas tardias accepted/refused/unknown/transport, PIX e recusa de reabertura de pagamento confirmado. Log local `C:/codex-data/tmp/infinitepay-minimum-redirect-postgres.log`. Não é aprovação da suíte backend integral de CI.
- No commit de preparação42a0326, classificador real confirmou `release_baseline_sha=21b89c3 / release_scope=app` e gate real `app_release_ready=true / somente_api_web`. PR draft [#266](https://github.com/conradodeita/markina-gallery/pull/266) criado, sem merge/deploy. Resultado final do CI remoto ainda não confirmado; falha de consulta GraphQL por timeout local não é falha comprovada do CI.

## Publicação futura

Serviços esperados: API e web, sem migration/worker/segredo/configuração financeira. CI, revisão, inventário e gates próprios antes de solicitar autorização. Rollback: imagens anteriores de API/web e SHA previamente saudável, preservando dados; não reinterpretar reservas antigas. Nenhum merge ou deploy autorizado para esta correção.

## CI confirmado e correção restrita do scanner — 22/10/2026 UTC

O [CI #779](https://github.com/conradodeita/markina-gallery/actions/runs/39693210865), head a93dfae1cfde2579ceebe8e05a6a6715d11fe80a, terminou **success**, com backend, frontend, OpenSpec, gitleaks, Gemma, imagens e política concluídos; duração total31m. Isso valida o checkpoint funcional, não o próximo head de metadados.

O CI780 do PR262 encontrou um falso positivo no recibo histórico de build b7f2090: indicador público de comparação de distribuições, sem credencial. A exceção contém apenas o fingerprint exato commit/arquivo/regra/linha. Regras, regexes, histórico completo e configuração do scanner permanecem preservados. O scanner pode alcançar esse commit quando buscar outras refs publicadas; por isso a mesma exceção revisável acompanha este PR.

- Gitleaks8.24.3 oficial, SHA256 verificado: clone temporário com ancestralidade completa deste candidato e ref publicada2a3e7f do cofre, sem refs locais não publicadas. Antes da exceção:1 achado histórico esperado/exit1. Depois:0 achados/exit0. Canário sintético independente:1 achado/exit1, confirmando detecção ativa. Relatórios integralmente redigidos; nenhum segredo operacional utilizado ou exibido.
- Regressão de escopo falhou antes da admissão exata de `.gitleaksignore`; após: **19 testes aprovados**,101,341s. Arquivo semelhante não listado continua recusado. Nenhum wildcard, endpoint, runtime, migration ou permissão de publicação do cofre acrescentado.
- Ruff dos scripts e política operacional aprovados após o ajuste. Blobs dos três arquivos de runtime permanecem iguais aos validados pelo CI779; os resultados funcionais anteriores conservam suas premissas. O novo head ainda requer CI remoto.

## Timeout de imagens do CI781 e matriz nativa

CI781/39699038564 no head320588ca:runtime-images/job119563500858 foi cancelado pelo limite30min durante Frontend ARM64 isolado e versões do lockfile, conforme anotação GitHub; não é aprovação final nem falha demonstrada de checkout. Gitleaks/OpenSpec/frontend/Gemma aprovaram; backend ainda concluía a matriz PostgreSQL na consulta.

Substituída somente a execução emulada por bloco runtime-images nativo idêntico ao já revisável em262, preservando builds API/frontend/facial/prévias/RAW e comparação de Next/React/ReactDOM quando aplicáveis, limite30min, fail-fastfalse e agregador obrigatório. Verificação local YAML:pares de runners/arquiteturas exatos, ausência de QEMU, timeout e dependência agregadora aprovados; teste de política completo e OpenSpec da change aprovados. Nenhuma mudança funcional/API/web, manifestos, pins ou permissões de release. O novo head exige CI final próprio.

## Fechamento do candidato funcional

[CI #783](https://github.com/conradodeita/markina-gallery/actions/runs/39702759942), head `b0af9944d19c454d68d8bf550731c97ff02eabf2`: **completed/success**, sem falha ou job pendente. Backend, frontend, imagens nativas AMD64 e ARM64, Gemma, scanner, OpenSpec e política agregadora concluídos com sucesso. O timeout emulado do CI781 foi superado sem ampliar limites ou remover verificações.

GO para revisão e solicitação de autorização de integração. Não houve merge/deploy. Publicação depende de revisão/autorização e inventário atual do candidato. O cofre integrado em262 continua sujeito ao plano próprio0085; esta aprovação não admite esse conjunto no workflow0084. Este fechamento altera apenas artefatos de evidência; conferir os checks do head documental no PR sem iniciar commits recursivos para citar o próprio SHA.
