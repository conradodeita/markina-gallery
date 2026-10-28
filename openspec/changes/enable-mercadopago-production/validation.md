# Evidências de validação

## Validação local do contrato existente — 27/10/2026

- Branch de trabalho: `codex/enable-mercadopago-production`, criada sobre `origin/main` em `960a1074`; a branch anterior era ancestral da `origin/main`, sem commits divergentes descartados. As notas locais preexistentes foram preservadas.
- Inspeção de `backend/app/mercadopago_settings.py`: `can_create` exige conta ativa e permite conta real somente quando `MERCADOPAGO_ALLOW_LIVE_PAYMENTS=true`; `effective_mercadopago` também exige preferência Mercado Pago habilitada no tenant, conta associada ao mesmo tenant, allowlist para contas de teste e disponibilidade do cofre cifrado.
- Inspeção de `docker/docker-compose.yml`: o gate global tem default `false`; a allowlist de clientes de teste é independente. As variáveis financeiras são injetadas no serviço API, enquanto o cofre é montado somente em API e worker.
- Inspeção de `backend/tests/test_mercadopago_operations.py` e `backend/tests/test_mercadopago_checkout.py`: cobrem gate live fechado, allowlist inválida/ausente, exigência exata do par tenant/cliente, isolamento entre clientes e continuidade da reconciliação/cancelamento após revogação da permissão de novas emissões.
- Comandos focados executados no ambiente virtual isolado `C:\codex-data\venvs\mp-prod-apply` com SDK `mercadopago==3.6.0`: módulos `test_mercadopago_operations.py`, `test_mercadopago_checkout.py`, `test_mercadopago_projections.py` — **34 passed, 2 skipped, 29 warnings, 139.47 s**; módulo `test_mercadopago_settings.py` — **5 passed, 11 warnings, 27.30 s**. Os skips e avisos foram reportados pelo pytest; não houve falha. Não houve chamada externa ao Mercado Pago nem cobrança.
- Avaliação proporcional de refatoração: não foi identificada alteração funcional necessária; os gates e a segregação já existem. A change documenta e operacionaliza o desbloqueio, sem mudar o código financeiro.
- `scripts/test_orders_pilot_release.py`: **44 testes aprovados, 1 skip existente** após acrescentar contrato do inventário 0090 com matriz sanitizada; `scripts/test_production_release_workflow_policy.py`: aprovado; Ruff nos três arquivos Python alterados: aprovado; `openspec validate enable-mercadopago-production --strict`: válido.

## Inventário read-only de produção

- Run `40618104905` (`workflow_dispatch`, SHA `960a1074ef711a8115345af4c43d26df66a5433f`): todos os gates gerais de CI passaram; o job read-only `orders-pilot-preflight` falhou antes de produzir inventário, com `orders-release: identidade_orders_divergente`. A causa é o helper antigo ainda exigir a identidade do baseline pré-0090. O job não preparou, aplicou ou alterou serviços.
- A release 0090 autorizada pelo proprietário é registrada no run `40612627547`, conclusão `success`, mesmo SHA de suporte `960a1074ef711a8115345af4c43d26df66a5433f`.
- Correção local: o helper read-only agora seleciona um caminho separado para schema `20261026_0090`; verifica SHA ativo ancestral ao código Orders já publicado e à `main`, gate e allowlist sem expor pares, chaves do cofre, saúde HTTPS, portas e marcadores pendentes, além de contar categorias de preferências sem IDs de tenant. O wrapper força o helper por blob exato e ganhou uma instalação manual protegida com backup. Testes locais passaram, mas essa versão ainda não foi integrada/instalada nem executada contra produção; a task 2.1 permanece pendente até o inventário novo gerar evidência.

## Limites ainda não validados

- O estado do gate no runtime publicado ainda não foi confirmado pelo inventário atual compatível; a execução anterior falhou antes dessa leitura. Não alterar o gate até a task operacional 2.1 produzir inventário e plano exatos.
- O estado real atual das configurações por tenant, quantidade de fotógrafos habilitados e saúde do runtime precisa ser obtido pelo inventário read-only de produção desta liberação. Não foram consultadas credenciais nem enviados pagamentos.
- HTTPS/saúde e elegibilidade efetiva por tenant só poderão ser confirmados após inventário e ativação autorizada; testes locais não provam a configuração do host.
