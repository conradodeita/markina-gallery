# Validação

## 28/10/2026 — preflight Orders não substitui inventário APP_ENV

- O CI do merge #336 (`40757983730`, SHA `cc62353d3e68b86f232b9a225d5c7791c6c771e0`) concluiu com sucesso. O wrapper SSH read-only foi atualizado pelo fluxo protegido `40760247201`; o job de instalação confirmou sucesso.
- A coleta `orders-pilot-inventory` `40762760966`, no mesmo SHA, passou pelos gates e validou serviços/portas, mas falhou fechado em `ambiente_divergente:outro_ambiente_conhecido`. O preflight Orders interrompe antes do schema, matriz de tenants, gate live, HTTPS e fingerprint; não revela o valor bruto de `APP_ENV`.
- Nenhum inventário/fingerprint APP_ENV, contagem de banco, confirmação de biometria ou classificação de integrações foi produzido. A operação foi somente-leitura: nenhum serviço, configuração, arquivo, banco, credencial, gate ou pagamento foi alterado.
- A conclusão do run confirma que o fluxo Orders não pode ser usado para a transição APP_ENV. O coletor remoto dedicado permanece pendente na task 3.1; até ele passar CI e retornar um relatório sanitizado, a transição e o plano de liberação geral continuam bloqueados.

## 28/10/2026 — inventário local (task 1.1)

- `rg` confirmou os consumidores de `APP_ENV`, classificadores `*_CREDENTIAL_ENV`, chaves de cofre e campos cifrados em `backend/app`; a matriz e a classificação criptográfica estão em `inventory.md`.
- O teste `backend/tests/test_app_env_transition_inventory.py` verifica que o conjunto e a contagem de linhas com marcadores ambientais/criptográficos não mudou sem revisão e que os serviços Compose que recebem `APP_ENV` continuam exatamente `api`, `worker`, `face-search-worker`, `face-index-worker` e `face-maintenance-worker`.
- `python -m pytest -q backend/tests/test_app_env_transition_inventory.py`: **2 passed**.
- `python -m ruff check backend/tests/test_app_env_transition_inventory.py`: **All checks passed**.
- No run read-only `40715456515`, o conjunto de serviços, saúde e portas passaram antes do bloqueio sanitizado `ambiente_divergente:outro_ambiente_conhecido`. O run não forneceu fingerprint completo, revisão de schema, matriz financeira nem contagem de dados cifrados. A composição ativa/quantidades reais permanecem desconhecidas e não foram inferidas dos arquivos Compose.
- Revisão focalizada: não foi encontrada ferramenta existente de transição ou re-cifragem para `APP_ENV`. Foram encontrados ciphertexts faciais cujo AAD inclui ambiente. Por serem dados biométricos, permanecem fora desta operação; inventário incompleto ou qualquer ciphertext facial vinculado à origem bloqueará a mudança global. Nenhum payload facial foi aberto.
- Nenhum arquivo de configuração de segredo foi lido; nenhum valor secreto, ID de tenant, payload cifrado, serviço de produção ou registro financeiro foi alterado.

## 28/10/2026 — contrato de inventário (task 1.2)

- Implementado `backend/app/environment_transition_inventory.py`: classifica `APP_ENV` sem copiar valores, aceita somente contagens/labels allowlisted, valida revisões, fingerprints de configuração, conjunto de serviços e categorias de bind/portas, e emite SHA-256 canônico somente quando todos os gates passam.
- O inventário exige os 15 serviços do contrato operacional atual, health saudável nos serviços ativos, ausência dos dois workers aposentados, somente bind `127.0.0.1:8080` no nginx, gate live fechado, integração externa classificada e contagens biométricas zeradas. Qualquer fonte desconhecida ou divergente produz blockers e fingerprint `null`.
- O recibo agrega as cinco categorias faciais sem abrir os payloads. `render_environment_inventory` rejeita chaves extras, valores com formato inesperado, checksum divergente e dados não sanitizados.
- `python -m pytest -q tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **12 passed**.
- `python -m ruff check app/environment_transition_inventory.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **All checks passed**.
- Os dados testados são sintéticos; nenhuma consulta ao banco de produção, inspeção de segredo ou operação remota foi realizada.

## 28/10/2026 — contextos explícitos e classificação (tasks 2.1, 2.4 e 2.5)

- `IntegrationCipher.from_explicit_context()` valida ambiente, igualdade do binding, keyring, chave ativa e comprimentos das chaves sem consultar `os.environ`; `for_environment()` cria o contexto de destino mantendo o keyring validado em memória.
- Os testes verificam AAD incompatível entre ambientes, chave/keyring inválidos, mensagem de erro sanitizada e preservação byte a byte das variáveis de processo.
- `classify_external_integrations()` classifica WhatsApp, SMTP e facial a partir de flags agregadas e sanitizadas: integração desligada, habilitada e validada para o destino, ou não classificada. Não recebe nem retorna credenciais. O fingerprint bloqueia qualquer integração não classificada.
- O contrato biométrico bloqueia fingerprint quando qualquer um dos cinco contadores de ciphertexts faciais é positivo; as fixtures cobrem embeddings, referências, localizadores, notificações e jobs sem abrir payloads.
- `python -m pytest -q tests/test_app_env_transition.py tests/test_integration_secrets.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **47 passed**.
- `python -m ruff check app/app_env_transition.py app/environment_transition_inventory.py app/integration_secrets.py tests/test_app_env_transition.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py tests/test_integration_secrets.py`: **All checks passed**.
- Revisão focalizada: o código de transição atualiza somente os dois campos de envelope da conta Mercado Pago; não há refatoração ou remoção de código existente elegível nesta área.
- Nenhum arquivo de segredo foi lido, nenhum payload facial foi aberto, nenhum tráfego externo foi emitido e nenhum dado operacional foi consultado ou alterado.

## 28/10/2026 — re-cifragem transacional (task 2.2, validação parcial)

- Implementados plano e execução local em `backend/app/app_env_transition.py`: validar origem/destino, descriptografar e validar os dois envelopes por tenant/ID de conta, comparar fingerprint antes da primeira escrita, bloquear tabela e linhas no PostgreSQL, re-cifrar/verificar no destino e atualizar somente `access_token_envelope` e `webhook_secret_envelope` em uma transação.
- Ensaios SQLite sintéticos confirmam preservação de tenants, preferências PIX/Mercado Pago, checkout key, revisão do carrinho, valores, estado e referências de pedido; fingerprint divergente aborta antes de escrever e erro na segunda conta reverte a transação inteira.
- Foi adicionado teste PostgreSQL opcional, restrito a `localhost`/loopback e ao banco com nome exato `app_env_transition_test`, usando schema aleatório próprio e removendo somente esse schema. `APP_ENV_TRANSITION_TEST_DATABASE_URL` não está configurada, portanto o teste foi ignorado; nenhum banco remoto ou operacional foi usado.
- Estes ensaios SQLite não demonstram as garantias concorrentes do PostgreSQL. A task 2.2 permanece pendente até executar o teste em um PostgreSQL de teste explicitamente isolado.

## 28/10/2026 — recuperação cifrada e gate operacional (tasks 2.3 e 3.1)

- Backup autenticado AES-GCM implementado com chave derivada via HKDF da chave de integração ativa e domínio separado. IDs, metadados das contas e envelopes originais ficam dentro do arquivo cifrado; o payload externo contém somente chave identificadora, contagem, categorias sanitizadas, fingerprint, nonce e ciphertext. O backup não inclui nem substitui a keyring: ela deve permanecer em armazenamento seguro separado até concluir a verificação e a janela de rollback.
- O backup inclui o contexto ambiental anterior cifrado; recovery valida autenticidade, fingerprint e cada envelope antes de gravar e restaura somente os dois campos de envelope, mantendo o contexto anterior disponível para o operador sem alterar `os.environ`.
- Ensaios sintéticos cobrem backup/restauração após transição, backup adulterado abortando antes da escrita e erro durante restauração revertendo todas as contas. Recuperação/configuração de serviços continua sendo etapa operacional manual descrita em `operations.md`; nenhuma configuração foi aplicada.
- O ensaio ponta a ponta `test_synthetic_runbook_roundtrip_has_no_secrets_or_external_calls` persiste e relê o backup cifrado em diretório temporário do teste, valida os gates, migra e restaura os envelopes sintéticos. O arquivo relido não contém os valores sentinela; o fluxo não invoca provedores externos.
- `execute_approved_mercadopago_transition()` exige fingerprint completo do inventário, confirmação textual que vincula inventário e contas, backup autenticado e declarado persistido/verificado, gate live fechado, zero contagens biométricas, integrações classificadas e a lista exata de consumidores próprios pausados. Fixtures testam aprovação válida e cada bloqueio antes da primeira escrita.
- A guarda local não pausa serviços e não prova que um operador realmente os pausou ou persistiu o backup; `paused_consumers` e `backup_storage_verified` são confirmações do executor. A task 3.1 continua pendente até ensaio operacional específico, sem parada ou alteração remota nesta execução.
- `python -m pytest -q tests/test_app_env_transition.py tests/test_integration_secrets.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py`: **58 passed, 1 skipped** (PostgreSQL de teste não configurado).
- `python -m ruff check app/app_env_transition.py app/environment_transition_inventory.py app/integration_secrets.py tests/test_app_env_transition.py tests/test_environment_transition_inventory.py tests/test_app_env_transition_inventory.py tests/test_integration_secrets.py`: **All checks passed**.

## 28/10/2026 — checkpoint de integração e revisão focalizada (task 3.3)

- Com o Python do venv `backend/.venv` (que contém `mercadopago==3.6.0`), `python -m pytest -q` nos quatro módulos novos/alterados e nos testes Mercado Pago de settings, schema, projeções, operações, checkout, worker, webhooks e disponibilidade: **128 passed, 4 skipped** em 296 s. Nenhuma falha observada; entre os skips está o PostgreSQL dedicado não configurado. Avisos emitidos foram de deprecações existentes do FastAPI/Starlette e warnings de DROP do fixture SQLite.
- `backend/.venv/Scripts/ruff.exe check backend/app backend/tests`: **All checks passed**.
- `backend/.venv/Scripts/python.exe -m compileall -q` nos módulos/testes alterados: **passou**.
- `openspec validate transition-app-env-bound-integrations --strict`: **change válida**; `git diff --check`: sem erros de whitespace. A política `docs/CONTINUOUS-REFACTORING.md` foi aplicada à área afetada; imports/lint e revisão não apontaram código substituído elegível.
- O backend não declara etapa de mypy/pyright/typecheck ou build em `backend/pyproject.toml`/CI; Python compileall e testes são a validação local aplicável.
- O commit inicial `61df1a8` foi enviado ao branch de feature. O ajuste de CI para PostgreSQL ainda está em alteração local. Nenhuma migration, configuração, serviço, credencial ou dado de produção foi alterado.
- Para executar a prova PostgreSQL pendente, o job `backend-tests` do CI agora cria um banco `app_env_transition_test` isolado em cada PostgreSQL descartável do shard e fornece sua URL somente ao teste opcional. O teste usa schema aleatório e remove somente esse schema. Parse do YAML do workflow e `python -m unittest scripts.test_classify_ci_scope -q`: **10 passed**. A task 2.2 só será marcada depois do resultado do teste PostgreSQL no CI.

## 28/10/2026 — prova PostgreSQL no CI (task 2.2)

- O primeiro CI `40735393207` executou o teste real no PostgreSQL isolado e revelou que o fixture adicionava tenant e cliente no mesmo flush, sem relacionamento ORM que garantisse a ordem das inserções. A falha foi corrigida somente no fixture, com flush explícito do tenant antes de cliente/conta; nenhum código de produção foi alterado por essa correção.
- Validação local após a correção: `backend/.venv/Scripts/python.exe -m pytest -q backend/tests/test_app_env_transition.py`: **15 passed, 1 skipped** (skip esperado sem URL PostgreSQL local); Ruff do arquivo passou.
- O CI do PR #335, SHA `947582a6b297e5ae650116b0369fef3dfc6c2e88`, run [`40737909487`](https://github.com/conradodeita/markina-gallery/actions/runs/40737909487), terminou **success**. Os três shards backend passaram; o shard 1 aprovou **543 testes, 5 skipped e 1096 deselected**. O banco `app_env_transition_test` foi provisionado no shard, e o teste PostgreSQL `test_postgresql_transition_locks_and_preserves_financial_rows` deixou de falhar; seus asserts verificam envelopes/credenciais por tenant, total, revisão do carrinho, status e ID da order.
- Também passaram `openspec`, `ci-scope`, `gitleaks`, `frontend`, `backend-quality`, imagens amd64/arm64 e `homolog-inventory-policy`. Os jobs de produção foram ignorados por escopo; isso não representa execução, prontidão ou aprovação da transição operacional em produção.
- Task 2.2 validada. Permanecem bloqueadas as tasks operacionais 3.1 e 4.1: não houve pausa real de serviços, inventário/fingerprint atual do servidor, comprovação de origem biométrica, backup operacional verificado ou execução da mudança em produção. Nenhuma credencial real foi trocada e nenhuma configuração, serviço ou dado de produção foi alterado.

## 28/10/2026 — coletor remoto APP_ENV (implementação local, task 3.1 pendente)

- Implementados `scripts/app_env_transition_inventory.py` e `scripts/app_env_transition_inventory_report.py`, a allowlist `MARKINA_APP_ENV_INVENTORY_TARGET_SHA` no wrapper restrito e o job manual `app-env-transition-inventory` em `production-preflight`. O script exige SHA igual a `origin/main`, checkout remoto limpo, blob do helper de contrato fixado e modo somente-leitura.
- A coleta verifica consistência por duas leituras dos containers, variáveis de runtime, Compose, keyring, banco e referências faciais; também exige checkout remoto limpo. API/worker e consumidores faciais têm seus bindings ambientais comparados; o gate live precisa estar fechado nos consumidores financeiros verificados. Vínculos WhatsApp são agrupados por categoria ambiental segura e estado, sem IDs ou telefones.
- `python scripts/test_app_env_transition_inventory.py`: **14 passed, 1 skipped**. O skip local é a checagem POSIX de permissões da keyring, incompatível com o host Windows; o mesmo teste está incluído no CI Linux.
- `python -m pytest -q backend/tests/test_environment_transition_inventory.py backend/tests/test_app_env_transition.py`: **38 passed, 1 skipped** (PostgreSQL dedicado local não configurado; a prova PostgreSQL isolada já passou no run `40737909487`).
- Ruff passou para o contrato, testes e scripts alterados; `compileall`, `bash -n` via Git Bash, os dois testes dinâmicos do ForcedCommand, `scripts/test_production_release_workflow_policy.py`, `openspec validate transition-app-env-bound-integrations --strict` e `git diff --check` passaram.
- A revisão final encontrou que a etapa do workflow não passava o destino SSH configurado; a chamada foi corrigida para usar o usuário e host de `production-preflight`, e o teste de política agora exige esse destino. A validação foi repetida após a correção: **38 testes backend passaram, 1 skip local**; **14 testes do coletor passaram, 1 skip POSIX local**; **2 testes do wrapper passaram**; Ruff, parse YAML, política do workflow, `bash -n`, `compileall`, OpenSpec estrito e `git diff --check` passaram.
- O CI inicial do PR `#337` (`40771097519`) falhou somente no lint novo com dois `EXE001` porque os scripts invocados por `python` continham shebang sem modo executável. Os shebangs desnecessários foram removidos e o blob permitido do coletor foi recalculado no wrapper; o CI da correção ainda precisa ser acompanhado.
- As fixtures verificam recibo sanitizado, comparação em memória de segredo/chaves, paridade de configurações API/worker, comparação de snapshots, recusa de comando arbitrário e saída de workflow com fingerprint vazio quando há bloqueios. Nenhuma consulta remota, leitura de credencial de produção, chamada a provedor, alteração de configuração, pausa de serviço ou escrita de produção foi feita nesta etapa.
- No registro inicial acima, a task 3.1 ainda aguardava CI, integração em `main` e execução remota; ela foi concluída pelo recibo fail-closed documentado na seção abaixo. Tasks 4.1 e 4.2 permanecem pendentes; não houve aprovação de um plano operacional específico nem troca de `access_token`/`public_key`.

## 28/10/2026 — primeira execução remota APP_ENV e preflight Orders

- CI de `main` `40774264727` concluiu com sucesso no SHA `fac2d384c34b8f024eadb9d291a6a1d6126adc15`.
- A instalação restrita do wrapper `40776283994` concluiu com `preview_wrapper_install=success`; a identidade instalada foi `root:root:755`, SHA-256 `42607b59e62a5f393a0656ca603e3a695ca0dc137631007b7ff54f1e775e7634`. O wrapper anterior foi preservado em `/var/backups/markina-gallery/preflight-ssh-wrapper-20261028T221400Z-preview-migration-fac2d384c34b`, SHA-256 `66d266eb0b9ed16409d59d90d9b421403b53f6c351cd66c1ac942c9a746b74e5`.
- O workflow `app-env-transition-inventory` `40778425249`, no mesmo SHA de `main`, passou CI e validou o relatório sanitizado real: `collection_status=incomplete`, bloqueio `coleta_incompleta`, inventário ausente e fingerprint indisponível. Por desenho, o recibo não revela qual fonte falhou; não há fingerprint que autorize mutação. A task 3.1 foi concluída somente quanto ao contrato e ao caminho fail-closed do coletor.
- O preflight Orders read-only `40780574819` passou os gates gerais de CI e falhou fechado no host com `ambiente_divergente:outro_ambiente_conhecido`. Não produziu fingerprint nem consultou a matriz de tenants/gate live depois da divergência. O valor bruto de `APP_ENV` não foi registrado nem exposto.
- Nenhuma configuração, serviço, schema, credencial, pedido ou pagamento foi alterado; nenhuma cobrança foi enviada. Tasks 3.2 e 4.1 permanecem bloqueadas por ausência de inventário completo/fingerprint e recibo de backup. A task 4.2 continua pendente porque o preflight Orders não produziu plano/inventário atual. Não trocar `access_token` ou `public_key` e não habilitar pagamentos reais até resolver a coleta e aprovar um plano operacional específico.

## 28/10/2026 — diagnóstico sanitizado da coleta incompleta (em validação)

- O recibo `coleta_incompleta` do run `40778425249` não identificou a fonte que falhou, por desenho. Não há como recuperar essa causa do recibo anterior.
- Para a próxima coleta, o contrato agora aceita somente `failure_category` de uma allowlist de códigos constantes; valores/exceções arbitrários viram `falha_interna`. O envelope continua sem inventário parcial, fingerprint ou aprovação.
- Validação local final: `python scripts/test_app_env_transition_inventory.py` — **18 testes, 1 skip**; o teste AST prova que todas as categorias literais emitidas por `require()`/`InventoryError` estão na allowlist; fixtures comprovam que categoria conhecida é preservada, exceção arbitrária vira `falha_interna`, e segredo/ID/caminho não aparecem no relatório. O validador rejeita categoria ausente, não textual ou fora da allowlist.
- Ruff nos três scripts, `bash -n scripts/production-preflight-ssh-wrapper.sh`, política do workflow, OpenSpec estrito das changes `transition-app-env-bound-integrations` e `enable-mercadopago-production`, e `git diff --check` passaram. O skip local é o teste de permissões POSIX, que roda no worker Linux do CI.
- O pin do wrapper para o novo blob do coletor foi atualizado. CI, integração desta correção em `main`, instalação protegida atualizada e nova coleta read-only ainda pendentes; a task 3.5 não está concluída.
