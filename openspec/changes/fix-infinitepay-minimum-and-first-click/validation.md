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

### Gate operacional ainda bloqueado

`python scripts/test_production_release_workflow_policy.py` recusa a árvore modificada na linha 156: **arquivo de runtime app diverge do blob revisado**. Os manifests continuam descrevendo o runtime publicado e não autorizam estes novos blobs/arquivo de navegação. Não foram alterados allowlists, pins, wrappers ou scripts operacionais para forçar aprovação. Preparação de um novo candidato publicável requer revisão e atualização explícita do manifesto exato, com autorização própria; isso não impede validar funcionalmente a correção ou apresentar o PR em draft, mas impede declarar CI/release aprovados.

### Gates ampliados executados

- `npm test -- --maxWorkers=2`: **67 arquivos / 605 testes aprovados**, 173,57 s. Inclui teste do adaptador `location.assign` sem popup e preservação do link/reserva se a navegação falhar.
- A primeira suíte frontend padrão, em paralelo com build/lint, terminou com **600 passed / 5 failed**, todos os cinco por timeout de 5 s em arquivos administrativos não alterados. Memória livre observada em cerca de 850 MB. Repetição integral com dois workers, sem build concorrente, passou sem aumentar timeouts ou alterar esses testes/configuração.
- `npm run lint`: **0 erros / 34 avisos preexistentes**, exit0.
- `npm run build`: **exit0**, compilação, TypeScript e geração de páginas concluídos.
- `python -m ruff check backend/app/provider_checkout.py backend/tests/test_provider_checkout.py`: aprovado.
- `npx -y @fission-ai/openspec@1.14.0 validate --strict --all`: **133 passed / 0 failed**, versão exata do CI. A CLI global local 1.14.1 teve 30 recusas por novas verificações em changes anteriores; nenhuma spec não relacionada foi alterada para contorná-las.
- `git diff --check`: aprovado. Revisão proporcional: reaproveitados mutex, idempotência, projeção e reservas; link de retomada continua necessário como fallback e para compras já emitidas. Nenhuma remoção extra ou refatoração ampla é elegível.
- Matriz ampliada PostgreSQL de 91 casos iniciada, resultado final ainda pendente neste checkpoint; não é aprovação de toda a suíte backend ou de CI.

## Publicação futura

Serviços esperados: API e web, sem migration/worker/segredo/configuração financeira. CI, revisão, inventário e gates próprios antes de solicitar autorização. Rollback: imagens anteriores de API/web e SHA previamente saudável, preservando dados; não reinterpretar reservas antigas. Nenhum merge ou deploy autorizado para esta correção.
