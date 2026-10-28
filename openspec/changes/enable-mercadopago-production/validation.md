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

## Correção do preflight de inventário 0090 — 28/10/2026

- PR #323 foi integrado na `main` (`1e1b36e7200a0f0d86787c5ea625f4ddb843865f`). CI do workflow de instalação do wrapper `40621982342` concluiu com sucesso, após aprovação do ambiente protegido `production`; a instalação restringe o acesso ao helper de inventário fixado por hash.
- O inventário read-only `40623205334` passou CI geral, mas o job `orders-pilot-preflight` encerrou antes das leituras de serviços e banco com `orders-release: checkout_nao_e_main`. O argumento do workflow já havia sido validado contra a ponta atual de `main`; a checagem redundante no helper comparava o checkout de produto da produção com a ponta de `main`, impedindo inventariar código de produto corretamente publicado quando `main` avança com suporte operacional.
- O job falhou fechado, sem alterar gate, serviços, configuração, banco ou pagamentos. Evidência precisa ser atualizada após correção e nova execução; a task 2.1 permanece pendente.
- Correção local para nova execução: a rota Orders agora compara o checkout remoto limpo com o SHA de `main` por ancestralidade e continua exigindo que o SHA-alvo recebido corresponda exatamente à ponta de `main`; imports usados apenas por preparação/release foram adiados para essas rotas, evitando dependência do helper de um checkout de produto anterior. O pin `ORDERS_SCRIPT_BLOB_SHA` foi recalculado para o helper revisado. Em `codex/fix-orders-live-inventory-checkout`, `python -m unittest test_orders_pilot_release -q` passou (**44 testes, 1 skip existente**), `python test_production_release_workflow_policy.py` passou e Ruff passou nos dois arquivos Python. `openspec validate enable-mercadopago-production --strict` também passou. A nova CI e o inventário remoto ainda não foram concluídos; a task permanece pendente.

## Nova tentativa e diagnóstico seguro — 28/10/2026

- Run `40627798409`, candidato `main` SHA `19a07e62614a52a0cd8df58e8685d2c3f40d0b78`: todos os gates gerais de CI e a política de inventário passaram. O job `orders-pilot-preflight` falhou na etapa `Inventário Orders read-only` com `orders-release: comando_operacional_falhou`, sem expor a etapa nem a causa do subprocesso.
- Não há fingerprint nem inventário emitido; a task 2.1 segue pendente. O comando terminou em modo somente leitura e nenhum gate, serviço, configuração, banco, credencial ou pagamento foi alterado.
- Correção em andamento: acrescentar ao helper rótulos estáticos de etapa em falhas operacionais, sem propagar argumentos ou saída do subprocesso; o próximo CI/preflight deverá permitir identificar o comando que falha mantendo a saída sanitizada.

## Relação de ancestralidade de produção — 28/10/2026

- Run `40632010932`, candidato `main` SHA `eaa23ecdb02e881d94b7618f6b0717b93d6293e5`: gates gerais verdes; o job read-only parou na etapa `verify_checkout_ancestry` antes de ler containers, banco ou matriz de tenants. A saída expôs somente o rótulo fixo, sem SHA ou dados sensíveis.
- O SHA de produto documentado para o runtime publicado, `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, é ancestral do `main` atual. Isso não explica a divergência do `HEAD` do checkout operacional. O inventário não deve prosseguir até identificar o HEAD real e confirmar sua proveniência; nenhuma guarda será removida por inferência.
- Ajuste local em andamento: distinguir resultado legítimo `git merge-base --is-ancestor` falso de falha de execução e, somente nessa condição, reportar os SHAs Git validados para permitir a reconciliação. Repetir CI, instalar o wrapper protegido e novo preflight ainda pendentes.

## Diagnóstico do subprocesso de ancestralidade — 28/10/2026

- Run `40650111265` no SHA `f9a3c15eec17a63ed3cdf9448976109ed7155abc`: CI e instalação protegida do wrapper concluíram com sucesso. A instalação alterou apenas o helper de inventário autorizado por hash; não abriu o gate nem reiniciou serviços.
- Run read-only `40651611371`, no mesmo SHA: os gates gerais passaram, mas `orders-pilot-preflight` falhou em `verify_checkout_ancestry` com `comando_operacional_falhou`. O erro não identifica a classe da exceção, portanto ainda não diferencia timeout, falha do sistema ou erro de subprocesso. O inventário e fingerprint não foram produzidos; nenhuma configuração financeira, serviço, banco ou pagamento foi alterado.
- Correção local: adicionar categorias estáticas sanitizadas para `TimeoutExpired`, `OSError` (somente errno numérico), `CalledProcessError` (somente status numérico) e outros `SubprocessError`; mensagens, argumentos, ambiente e saídas permanecem omitidos. A guarda de ancestralidade e o fail-closed não mudam.
- Validação da correção, nova CI, instalação do helper fixado e execução do preflight continuam pendentes. A task 2.1 segue aberta até que o inventário read-only gere evidência completa e revisável.

## Retorno Git fora dos códigos de ancestralidade — 28/10/2026

- O workflow read-only `40657916527`, no SHA `a6bc471da33aef6324381908eb0e92eacedcc958`, falhou em `verify_checkout_ancestry` com o texto genérico. O job de instalação no mesmo SHA (`40656462828`) confirmou `preview_wrapper_install=success`; o helper de `main` continha o novo tratamento sanitizado por tipo, mas ainda emitia erro genérico quando o código retornado por `git merge-base --is-ancestor` não era `0` ou `1`.
- A saída pública não registra o status Git efetivo; portanto não se presume a causa específica. Correção local: reportar somente o número do status inesperado junto ao estágio estático, sem argumentos nem saída do Git. O retorno `1` permanece a interpretação normal de não ancestralidade.
- O preflight permaneceu somente leitura e não produziu inventário/fingerprint. Gate, serviços, banco, credenciais e pagamentos não foram alterados. A correção, CI, instalação e novo inventário ainda estão pendentes.

## Diagnóstico de objetos Git indisponíveis — 28/10/2026

- Run `40664700464`, no SHA `0c0018dd6ef885a63df8054d1bc9f743cf0151df`, confirmou `exit_status_128` em `verify_checkout_ancestry`. Esse status ocorre no helper instalado quando `git merge-base` retorna valor diferente de `0` ou `1`; a mensagem anterior omitia o número.
- Correção local: após status anormal, consultar somente `git rev-parse --is-shallow-repository` e `git cat-file -e` para cada commit; a mensagem pública informa estados booleanos de repositório raso e presença dos objetos, nunca os SHAs nem saída textual. A guarda continua fail-closed.
- O run falhou antes de gerar inventário/fingerprint e não alterou gate, serviços, banco, credenciais ou pagamentos. Testes focados, CI, instalação e nova execução read-only ainda pendentes.

## Falha isolada do teste Vitest — 28/10/2026

- Run de instalação `40670222739`, após CI das alterações locais, falhou no teste `checkout.test.tsx` “atualiza o carrinho quando polling recupera a confirmação”; `homolog-inventory-policy` e o contexto legado falharam como consequência. Nenhum job de instalação ou preflight de produção executou.
- O cenário foi reproduzido localmente. Correção test-only: usar spy call-through para manter os timers de `waitFor` e capturar somente o callback de polling do pagamento. O teste isolado passou após essa mudança; não altera o comportamento do checkout. Lint, arquivo completo, CI e novo workflow protegido ainda pendentes.

## Limites ainda não validados

- O estado do gate no runtime publicado ainda não foi confirmado pelo inventário atual compatível; a execução anterior falhou antes dessa leitura. Não alterar o gate até a task operacional 2.1 produzir inventário e plano exatos.
- O estado real atual das configurações por tenant, quantidade de fotógrafos habilitados e saúde do runtime precisa ser obtido pelo inventário read-only de produção desta liberação. Não foram consultadas credenciais nem enviados pagamentos.
- HTTPS/saúde e elegibilidade efetiva por tenant só poderão ser confirmados após inventário e ativação autorizada; testes locais não provam a configuração do host.

## Retomada do inventário de liberação geral — 28/10/2026

- Worktree confirmado: branch `codex/fix-checkout-polling-test-spy` em `dd2e382b`; notas locais preexistentes da change `fix-card-brick-readiness` foram preservadas e não incluídas. A correção prosseguiu em branch nova baseada na ponta atual de `origin/main`, `243d9a1dd6a8af7596b080504d985bce272479e9`.
- Run de instalação do wrapper read-only `40674679164` (`main`, SHA `243d9a1d`) passou CI e concluiu com sucesso após a aprovação protegida limitada à instalação do helper por hash. Nenhuma mudança de gate, serviço, banco, credencial ou pagamento foi autorizada ou executada.
- O inventário `40676570904` passou os gates gerais, mas `orders-pilot-preflight` falhou antes de produzir inventário/fingerprint. Diagnóstico sanitizado: `verify_checkout_ancestry:exit_status_128:shallow_false:ancestor_commit_present:descendant_commit_unknown`. A verificação local `git merge-base` não tem o objeto de `main` atual no checkout operacional; isso não prova divergência de histórico.
- Conferência independente pelo endpoint GitHub REST de comparação entre o commit de produto conhecido `0dd015a62447e0c8d4c6af16b381140c8118f2ec` e `main` em `243d9a1dd6a8af7596b080504d985bce272479e9` retornou `status=ahead`, `ahead_by=78`, `behind_by=0`, e `merge_base_commit` igual ao commit de produto. Isso confirma a relação histórica para esse par conhecido, mas não substitui a leitura read-only do `checkout_sha` real do servidor.
- Para evitar gravação no `.git` operacional, a correção usa a API pública oficial de comparação do GitHub, exigindo que o merge-base retornado seja exatamente o checkout solicitado; erros, resposta divergente ou inacessibilidade permanecem fail-closed. O pin SHA-1 Git do helper no wrapper restrito foi atualizado junto com o conteúdo do helper.
- Validação local desta correção: `python -m unittest test_orders_pilot_release -q` — **53 testes, 1 skip existente**; Ruff nos dois arquivos Python — aprovado; `test_production_release_workflow_policy.py` — aprovado; `openspec validate enable-mercadopago-production --strict` — válido; `git diff --check` — aprovado (avisos de conversão de EOL somente nos dois arquivos locais preexistentes da outra change).
- O teste da API pública no estado observado confirmou a relação do commit de produto já documentado com o candidato atual de `main`, mas a nova implementação ainda não passou pelo CI, não foi instalada no servidor e não foi executada no checkout real de produção. Gate real permanece sem alteração; nenhuma cobrança foi enviada.

## Inventário após validação remota de ancestralidade — 28/10/2026

- PR #331 (`94f8ca2c`) integrou a comparação de ancestralidade pela API oficial do GitHub; o CI do PR passou. O CI pós-merge `40680877971` teve uma falha transitória no teste Vitest `public-gallery.test.tsx` (foco no título após confirmação); o teste isolado local passou e a repetição somente dos jobs falhos, tentativa 2, concluiu com sucesso. O resultado de `main` no SHA `233f8d97964ba8458913b3e402efe4da31128c2c` está verde na tentativa 2.
- O wrapper read-only foi instalado com sucesso no run `40682754546`, SHA `233f8d97`, usando o blob do helper integrado.
- O inventário `40684822323`, SHA `233f8d97`, passou os gates gerais e a verificação de ancestralidade remota. Em seguida, falhou fechado em `servicos_incompletos`, antes de produzir inventário/fingerprint. Essa evidência prova que o bloqueio anterior foi resolvido, mas o conjunto de serviços ativos ainda não foi identificado.
- Correção em andamento: a falha reportará somente nomes ausentes da allowlist estática de serviços e presença/ausência da configuração API; não exporá IDs, imagens, env ou labels desconhecidos. O próximo CI, instalação por hash e inventário permanecem pendentes. Gate real, serviços, banco, credenciais e pagamentos não foram alterados por esse preflight.

## Reconciliação do conjunto de serviços do runtime — 28/10/2026

- O diagnóstico do run `40692056506` mostrou exatamente dois serviços esperados pelo helper que não aparecem entre containers em execução: `face-gemma-index-worker` e `raw-development-worker`; a API estava presente. A documentação de deployment da aposentadoria registra ambos encerrados graciosamente em 26/10, com estado e imagens preservados para recuperação. Assim, o conjunto esperado para inventário ativo é os outros 13 serviços; não se deve iniciar ou excluir os dois aposentados.
- A correção local exige todos os outros serviços conhecidos, rejeita se qualquer serviço aposentado estiver ativo, inclui todos os serviços observados no fingerprint e mantém falha fechada para omissões da lista ativa. Validação local: `python -m unittest test_orders_pilot_release -q` — **56 testes, 1 skip existente**; Ruff — aprovado; política do workflow — aprovada; OpenSpec estrito — válido. O hash fixado no wrapper foi atualizado. PR/CI, instalação do helper e repetição do inventário ainda pendentes. Gate, serviços, banco, credenciais e pagamentos permanecem sem alteração.
