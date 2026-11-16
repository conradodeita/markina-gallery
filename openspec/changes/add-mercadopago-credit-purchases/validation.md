# Validação: compra de créditos via Mercado Pago

## Escopo executado

- Implementação e validação somente no worktree local. Nenhuma migration foi aplicada em homologação ou produção. Foram usados dados sintéticos e uma conta Mercado Pago confirmada como test_user em validação externa local, conforme relatório específico; nenhum pagamento real foi criado.
- `MercadoPagoCreditPurchase` e `MercadoPagoCreditPurchaseEvent` separam tenant comprador do tenant/conta recebedora do proprietário. A inspeção de metadata SQLAlchemy confirmou FKs compostas, unicidades escopadas e índices de reconciliação/revisão. As migrations financeiras 0094/0095 foram executadas em schemas sintéticos no PostgreSQL 17 local descartável; o baseline das dependências desse teste é criado pelo ORM.
- A revisão proporcional do diff não identificou código de venda de fotografias a remover. `MercadoPagoPayment`, `SaleOrder` e `SaleOrderItem` mantêm seus consumidores e semântica; a compra de créditos é aditiva. O worker ignora compras `prepared`/`abandoned`, que ainda não têm Order reconciliável.
- Os testes executados nesta etapa receberam um `DATABASE_URL` SQLite único em arquivo temporário por processo; não usaram o banco local padrão.

## Validação PostgreSQL concluída em 2026-11-01

- Foram aprovados **37 testes em 214,02 segundos**, sem skips, em `test_photographer_credits.py`, `test_mercadopago_credit_purchases.py` e `test_tenant_credit_purchase_postgres.py`. Os avisos foram de depreciação FastAPI já existente.
- O PostgreSQL local foi criado exclusivamente para esta execução, com imagem já disponível `postgres:17.11-alpine`, porta `127.0.0.1:15470`, banco sintético `pyp_photographer_test` e dados em tmpfs. Outros containers locais e o servidor de produção não participaram dos testes.
- Ao terminar, a identidade e o label do container foram conferidos e somente esse container temporário foi encerrado, com remoção automática; o PostgreSQL isolado preexistente permaneceu em execução. O JSON de credenciais foi criado somente com placeholders fora do repositório, a pedido do proprietário, e os valores reais ainda não foram fornecidos.
- O novo arquivo PostgreSQL cria schemas UUID exclusivos e aplica o DDL real de 0094/0095 sobre as tabelas de dependências do ORM. Comprova rejeição da conta recebedora pertencente a outro tenant, imutabilidade do preço congelado e recusa de UPDATE/DELETE/TRUNCATE do histórico. Duas sessões concorrentes confirmando a mesma Order geram somente um movimento de crédito e um evento confirmado.
- O conjunto também executou a concorrência de reservas da carteira, os estados financeiros, assinatura/replay, autorização de revisão, múltiplos bloqueios e ausência de débito automático. Ruff e compileall do novo teste passaram.
- O bootstrap legado de `backend/conftest.py` injeta tenant sem proprietário para módulos antigos. O novo módulo usa o prefixo `test_tenant_`, convenção já existente para excluir esse seed; a migration mantém sua recusa de bases com proprietário ambíguo.
- Após o conjunto de 37 testes, o módulo PostgreSQL foi ampliado e passou 3/3: o teste adicional executa a cadeia Alembic até 0090, insere proprietário/tenant sintéticos, aplica 0091→0095 e confere a identidade preservada, o TOTP cifrado e o backfill owner ilimitado/outro tenant finito. É ensaio sobre dados sintéticos, sem restore de snapshot produtivo. Nenhuma credencial, dado ou cópia do banco de produção foi utilizada.

## Pré-validação externa em 2026-11-01

- O proprietário preencheu o arquivo local protegido fora do repositório. A consulta real `OrdersProvider.identity()` confirmou `test_user` e site MLB. Nenhum token, Public Key, segredo de webhook ou identificação pessoal foi exibido ou incluído no repositório.
- `OrdersProvider.payment_methods()` real confirmou Visa e Mastercard de crédito ativos; não retornou PIX para essa conta. O formulário oficial `cardPayment` Brick carregou em navegador de teste com `onReady` e secure fields HTTP 200, usando a Public Key fornecida. Isso ainda não comprova tokenização nem criação de Order.
- A URL de teste trycloudflare informada não respondeu e não havia processo cloudflared local. Foi obtido temporariamente o binário oficial cloudflared 2026.10.7 para preparar callback isolado, com SHA-256 conferido contra o digest oficial `2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343`. Ele não foi instalado globalmente nem faz parte do runtime de produção.
- A revisão encontrou e corrigiu o encerramento prematuro da reconciliação manual de compras confirmadas/inativas. O teste direcionado consulta o provider pela conta recebedora, descobre reembolso parcial/total/chargeback, abre hold e preserva o ledger. A suíte ampliada passou 15/15 em SQLite temporário; os 15 testes de compra e os 3 de DDL/migrations passaram juntos **18/18 em PostgreSQL 17**, em 124,60 segundos. O filtro de polling periódico do worker foi preservado.
- Após a pré-validação, foram criadas três Orders de teste (APRO/OTHE/CONT), recebidos callbacks do provedor e executados replays controlados, reembolso parcial/total e revisão manual. Resultados e limites estão em `external-validation-results.md`. Naquele checkpoint, a task 4.2 aguardava revisão; o proprietário aceitou os limites em 02/11/2026 e a task foi concluída.
- Foi acrescentado ensaio pela página real autenticada com sessões sintéticas, em cópia temporária dos fontes para preservar o Next local preexistente. Uma quarta Order de teste foi confirmada: a UI atualizou saldo 0→12 e mostrou Compra 91476901; a visão do proprietário mostrou o mesmo ledger. Desktop e mobile foram inspecionados; 17 testes frontend, ESLint/TypeScript e build passaram após corrigir texto obsoleto e falso vazio da busca. Detalhes e caminhos das capturas em `external-validation-results.md`.
- O receptor de assinatura foi ajustado ao manifest bruto do SDK 3.6.0, preservando a variante minúscula legada sob HMAC válido. Os testes ampliados passaram **24/24 em SQLite temporário**, com validação independente do SDK e oito cenários de adulteração. O callback real e os replays nos dois formatos foram aceitos pelo receptor; variantes inválidas retornaram 401. Nenhuma alteração no filtro do worker ou semântica de pagamentos fotográficos.
- Checkpoint final após as correções: `test_mercadopago_credit_purchases.py`, `test_tenant_credit_purchase_postgres.py`, `test_mercadopago_checkout.py` e `test_mercadopago_worker.py` passaram com **46 aprovados, 1 ignorado**, em 458,49 segundos. Os testes de crédito/DDL usaram PostgreSQL descartável; os fixtures antigos de checkout usam bancos temporários próprios. Ruff, compileall, OpenSpec strict e whitespace passaram.
- O proprietário confirmou ter atualizado somente a URL de Webhooks de teste para o túnel local exclusivo. O endpoint público expõe apenas health e receptor assinado; formulário e controles ficaram restritos a localhost. A configuração produtiva não foi consultada nem alterada.

## Baseline de produção e paridade observada em 2026-11-01

- Consulta somente leitura confirmou `/api/health` com HTTP 200. Os serviços relevantes `api`, `web`, `worker`, `nginx`, `db`, `redis` e `preview-adjustment-worker` estavam `healthy`; a imagem do banco declara PostgreSQL 17.
- O container API reportou `APP_VERSION=74f61300e7a818d1605afda3db1d07574c443110` e a consulta `alembic current` reportou schema `20261026_0090`. O commit da API é ancestral do `origin/main` vivo, seis commits atrás. O commit do web não foi identificado pelo inventário disponível.
- O checkout remoto estava limpo em `0dd015a62447e0c8d4c6af16b381140c8118f2ec`; seu `origin/main` local era `cef5bdf82e254ec908d238aa3a5d09f1069e3cfd`. Consulta `git ls-remote` feita no próprio servidor confirmou que o `main` remoto vivo era `6af538ecd5c46da7691fa973c33869f263945a25`. O checkout remoto é ancestral desse main, mas seu ref local não está atualizado.
- O worktree local está na branch `feature/pickyourpic-saas-mainline`, com `HEAD` e `origin/main` local em `6af538ecd5c46da7691fa973c33869f263945a25`, além de alterações locais não commitadas. As migrations locais `20261031_0091` a `20261101_0095` avançam do schema de produção `20261026_0090` até o schema da change; nenhuma foi aplicada em produção.
- O wrapper de inventário de release, usando o SHA atual de main, abortou antes de consultar containers porque o `origin/main` local do checkout remoto não coincide com o alvo. Nenhum `fetch`, atualização de refs, teste, migration, alteração de container ou escrita no banco foi executado. A inspeção de runtime subsequente foi somente `docker ps/inspect`, leitura de `APP_VERSION`, `alembic current` e GET público de health.
- Isso confirma que observar produção é um gate útil de compatibilidade, mas não estabelece paridade total: a API reporta versão identificada, o commit web ainda é desconhecido, e os testes locais dessa change usaram SQLite enquanto produção usa PostgreSQL 17. Posteriormente foram aprovados testes PostgreSQL 17 e um ensaio sintético do upgrade 0090→0095, registrados acima; a base produtiva não é alvo de testes.

## Evidências locais

- `tests/test_mercadopago_credit_purchases.py`: **9 passaram** após a chave de auditoria de revisão manual passar a usar UUID, evitando colisão quando ações do proprietário ocorrem no mesmo instante.
- Conjunto `test_mercadopago_credit_purchases.py`, `test_mercadopago_checkout.py` e `test_mercadopago_worker.py`: **28 passaram, 1 ignorado**. Inclui contrato Orders e regressão do checkout de fotografias.
- `test_media.py::test_admin_imports_jpeg_to_private_source_and_queues_processing`: **1 passou** com fixture que cria explicitamente a carteira ilimitada do proprietário.
- Frontend `/admin/credits`: **17 testes passaram**. `npm run lint` terminou sem erros (36 avisos em arquivos do frontend, sem avisos nos componentes novos de créditos); `npx tsc --noEmit` e `npm run build` passaram. O build gerou a rota `/admin/credits`.
- Ruff passou para os arquivos backend alterados e `compileall` passou na rodada anterior. `openspec validate add-mercadopago-credit-purchases --strict` passou. `git diff --check` não reportou erros de whitespace; mostrou apenas aviso LF/CRLF em `backend/tests/test_admin_security.py`, fora da change.
- A revisão do diff confirmou que o evento append-only registra cada ação do proprietário e que decisões `restrict`/`release` não debitam créditos automaticamente. Replays do mesmo timestamp de Order são idempotentes; uma nova transição financeira pode abrir nova revisão.

## Suíte backend ampla e impacto no banco local

- Uma execução anterior da suíte completa terminou com **1741 passados, 95 ignorados, 5 falhas e 12 erros**. Ela não tinha `DATABASE_URL`; portanto usou `backend/markina-gallery.db`. O fixture autouse de `test_media.py` executa `Base.metadata.drop_all()` e `create_all()` nesse banco. Tabelas/dados locais podem ter sido removidos e recriados. Desde a identificação do impacto, o arquivo não foi alterado novamente; o conteúdo de registros não foi examinado e nenhuma tentativa de recuperação foi feita.
- Após autorização expressa do proprietário em 01/11/2026, fiz inventário somente leitura de nomes, caminhos, tamanho, data de modificação e SHA-256; em sete candidatos rodei apenas `PRAGMA quick_check` com URI `mode=ro&immutable=1`. Não consultei linhas nem alterei, copiei, movi ou restaurei arquivos.
- Recalculei os SHA-256 dos sete arquivos verificados após os checks; todos permaneceram iguais aos valores iniciais.
- O banco afetado, `backend/markina-gallery.db`, tinha 3.407.872 bytes, SHA-256 `A3E58EDBFEB95215FEC03DF1BDF29485A93CB7155086C9E7FE775C96D3F5C352` e modificação em `2026-11-01T18:54:25Z` (15:54:25 em São Paulo). `quick_check` retornou `ok`, o que confirma somente integridade estrutural SQLite; não confirma presença ou completude dos dados anteriores aos testes.
- Não havia arquivo `-wal`, `-shm` ou `-journal` com o nome desse banco na pasta afetada durante o inventário.
- Para entender se snapshots plausíveis têm dados de aplicação, consultei somente nomes de tabelas e contagens agregadas selecionadas, sempre com `mode=ro&immutable=1`; nenhum valor de linha foi lido ou exibido. Resultado:

| Candidato | Tabelas | Contagens agregadas observadas |
|---|---:|---|
| Banco afetado no backend do worktree | 107 | tenant 1; admin 1; galeria 1; pasta 1; foto 1; cliente 0; pedido 0 |
| Banco na raiz do mesmo worktree | 105 | tenant 1; admin 1; PlatformOwner 1; galeria 1; pastas 3; fotos 2; cliente 1; pedidos 0 |
| Checkout de origem, `backend/markina-gallery.db` | 77 | admin 1; galeria 1; pasta 1; foto 1; clientes 2; pedidos 4 |
| Checkout de origem, banco na raiz | 76 | zero nas tabelas de aplicação selecionadas que existem |
| Worktree `mercadopago-orders` | 98 | tenant 1; admin 1; galerias 2; pastas 3; fotos 3; clientes 2; pedidos 2; itens 3 |
| Cópia temporária `payment-status-release` | 95 | tenant 1; admin 1; galeria 1; pasta 1; foto 1; clientes 2; pedidos 2 |
| Arquivo `before-local-migration` | 18 | admin 1; galeria 1; foto 1; cliente 0; pedido 0 |

- As contagens mostram que o arquivo na raiz do mesmo worktree e alguns snapshots anteriores contêm linhas, mas não permitem distinguir dados reais de fixtures de teste. O banco afetado também tem algumas linhas após o fixture; não é possível inferir que sejam registros anteriores aos testes. Portanto nenhum dos candidatos foi aprovado como recuperação.
- Candidatos observados, todos com SHA-256 diferente do arquivo afetado e `quick_check=ok`: banco na raiz do mesmo worktree (3.321.856 bytes, `2026-11-01T02:00:19Z`, SHA-256 `3B86857EE9C5B8DCA7739A79B2841AF40DB5D25BD7DA23A863ACA76ACE10E7B4`); `C:\Users\Conrado\Documents\Photo Delivery\backend\markina-gallery.db` (1.978.368 bytes, `2026-10-17T01:54:18Z`); cópia raiz desse checkout (1.949.696 bytes, `2026-10-14T17:48:33Z`); worktree `mercadopago-orders` (3.162.112 bytes, `2026-10-28T17:16:10Z`); e cópia temporária `payment-status-release` (3.072.000 bytes, `2026-10-15T20:03:26Z`). Os hashes completos foram coletados localmente; nenhum candidato foi confirmado como backup lógico da base afetada.
- Há ainda o arquivo explicitamente nomeado `backend/markina-gallery.before-local-migration-20260826-1947.db` (339.968 bytes, `2026-08-26T22:32:44Z`, SHA-256 `DD3C9C2FAB4B9BAB91641E56B93FCEE7368FCC41AA27038FE491CA98BEAF7159`); `quick_check=ok`, mas ele é histórico, difere do alvo e não foi validado logicamente. A busca encontrou outras bases locais em worktrees acessíveis: todas as hashes coletadas diferem da base afetada e seus nomes/contexto não provam que sejam backups. A varredura ampla não conseguiu ler três subpastas `.codex-tmp/order-delivery-*` por `Acesso negado`; elas não foram abertas por outro meio.
- Não há cópia exata identificada. O banco na raiz do mesmo worktree é o candidato mais próximo no tempo, mas sua origem e conteúdo continuam desconhecidos. Nenhuma cópia foi selecionada para recuperação; qualquer restauração ou cópia para o caminho ativo exige decisão e autorização posterior do proprietário.
- A falha de mídia dessa execução foi corrigida no fixture e o teste isolado passou. A falha de `test_mercadopago_schema.py::test_upgrade_preserva_registros_e_acrescenta_contratos` ocorre na migration anterior `20261024_0088_mercadopago_orders.py`, que não encontra `ck_admin_security_purpose`.
- As falhas em `test_tenant_commerce.py::test_mesmo_telefone_compras_pix_destinatarios_e_historico_independentes` e `test_tenant_notification_transport.py::test_pagamento_de_grupo_envia_somente_admin_proprio` reportam destinatários de outro tenant. A segunda reproduziu em execução isolada com banco temporário. São achados de isolamento multi-tenant fora do escopo desta change e ainda não foram corrigidos.
- `test_tenant_producers.py::test_origem_recebe_contexto_e_edicao_preserva_proprietario` falhou isoladamente com `sqlite3.OperationalError: database is locked`. Os 12 erros em `test_tenant_installation_operator.py` registraram conflitos `UNIQUE` em `platform_owner.singleton` e banco SQLite bloqueado. Permanecem sem investigação/correção nesta change.
- Logo, a suíte backend ampla não está verde. Seu resultado não é evidência de regressão causada por esta change: o teste focado, o conjunto Orders e a mídia passaram em bancos temporários, mas os achados acima continuam explicitamente pendentes.

## Gates restantes

- **PostgreSQL dedicado:** gate local concluído com os resultados acima. A task 4.1 está concluída. O container temporário exclusivo pode ser recriado com a mesma imagem e porta para repetir a suíte; os dados sintéticos são descartáveis.
- **Mercado Pago de teste:** credenciais fornecidas e conta de teste confirmada por consulta real. Tokenização/create/get, callbacks reais e replays, reembolsos e revisão foram exercitados; os limites de PIX indisponível, chargeback externo não simulável e aprovação tardia não forçável estão registrados em `external-validation-results.md` e foram aceitos pelo proprietário em 02/11/2026. A task 4.2 está concluída.
- Nenhum resultado local autoriza migration, transação, configuração externa ou publicação em homologação/produção.

## Fontes oficiais consultadas em 2026-11-01

- [Criar Orders pela Checkout API](https://www.mercadopago.com.br/developers/en/reference/online-payments/checkout-api/create-order/post)
- [Notificações e validação de assinatura](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/optional-notifications)
- [Estados de uma Order](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-management/status/order-status)
- [Contas de teste específicas de Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/resources/test-accounts)
- [Cartões e cenários de teste Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/cards)
- [PIX de teste Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/integration-test/pix)
- [Release oficial cloudflared 2026.10.7](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.7)


## Reconciliação das fixtures da regressão ampla — 01/11/2026

Triagem dirigida, somente em SQLite temporário exclusivo, reproduziu três falhas commerce/transport/producer (64,63s), uma falha do DDL0088 (2,02s) e um erro representativo installation_operator (17,17s). Não consultou nem alterou produção ou o banco da jornada em15471.

Causas e correção planejada, sem alterar código de produção/migrations:

- O graph compartilhado adicionou um segundo administrador verificado ao tenant A para ser PlatformOwner. As suítes commerce/transport presumem um administrador por tenant; installation_operator tenta inserir outro singleton e espera somente dois vínculos. Extrair construtor com variante explícita owner=primeiro administrador para essas três suítes, preservando o graph padrão usado pelas demais. Manter as assertions existentes de isolamento e destinatários.
- test_tenant_producers concede créditos com flush depois do commit da fixture: adicionar commit antes de abrir TestClient, evitando escrita concorrente de uma transação de setup ainda aberta.
- test_mercadopago_schema mantém dois CHECKs nomeados na mesma linha do DDL SQLite sintético; separá-los por newline para reflexão correta antes de batch_alter_table. A migration0088 permanece preservada.
- A validação deve repetir os arquivos afetados; a suíte ampla anterior não será declarada verde por esses ensaios isolados.


### Resultado da reconciliação das fixtures

Implementado e validado sem alterar código de produção, migration histórica ou assertions de isolamento:

- `build_graph(..., owner_is_first_admin=True)` é uma variante explícita nas suítes commerce, notification_transport e installation_operator. O graph padrão das outras suítes continua criando a identidade adicional anterior. A fixture diagnostic não insere outro PlatformOwner. As expectativas originais de destinatários e contagens foram preservadas.
- O grant da fixture producer é commitado antes da sessão HTTP.
- Os dois CHECKs do DDL SQLite sintético0088 passam a linhas separadas para reflexão.
- Seis arquivos completos, SQLite TEMP exclusivo: **80passed,4skipped**,6avisos,924,28s. Foram incluídos commerce, transport, producers, mercadopago_schema, installation_operator e ownership_schema. Nenhuma falha nem erro.
- Três dos quatro skips foram executados separadamente em PostgreSQL17 exclusivo em127.0.0.1:15470/pyp_photographer_test, com schemas aleatórios próprios: **3passed**,6avisos,21,37s. Cobrem suspensão durante consulta de canal, revogação de membership durante envio e catálogo de constraints.
- O único cenário restante ignorado exige o ambiente histórico específico de test_mercadopago_schema em127.0.0.1:55888/markina_unified_test. Esse teste não foi apontado a outro banco nem marcado como executado.
- Ruff nos seis arquivos passou; git diff--check passou. Os ajustes desta rodada são somente fixtures e infraestrutura sintética de testes. Os arquivos já possuíam mudanças locais da carteira, mantidas integralmente.
- Logs fora do Git: `C:/codex-data/temp/pyp-mp-external-20261101/fixture-regression.log` e `fixture-postgresql-contracts.log`.

Essas evidências substituem o estado das falhas específicas reproduzidas da regressão anterior. **Não representam uma nova execução da suíte backend inteira**. Antes de release permanece necessário o checkpoint amplo, a revisão dos limites externos e os gates operacionais; nenhuma publicação está autorizada.

## Tentativa da suíte completa e bloqueio local — 02/11/2026

- Comando: `.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short -r a --basetemp=C:/codex-data/temp/pyp-backend-final-pytest-20261102`. `DATABASE_URL` apontou para SQLite exclusivo em `C:/codex-data/temp/pyp-backend-final-20261102/app.sqlite`; `PHOTOGRAPHER_TEST_DATABASE_URL` apontou para o PostgreSQL sintético exclusivo `127.0.0.1:15470/pyp_photographer_test`. Nenhum acesso ao banco de produção foi configurado.
- A execução imprimiu progresso até **68%**, com dois erros (`EE`) e 11 skips já observados até o marcador de 64%. Não houve `F` visível antes da interrupção. O resumo pytest, nomes dos dois testes e tracebacks não foram produzidos; portanto, não é possível classificar os erros nem afirmar resultado final.
- O processo ficou sem atualizar log e sem progresso por mais de dez minutos. O processo ainda mantinha uma conexão TCP com o PostgreSQL sintético, mas uma nova conexão SQLAlchemy a `127.0.0.1:15470`, com timeout de 5 segundos, expirou. Consultas locais somente de leitura ao container via `docker exec` e `docker ps --filter name=pyp-credit-external-20261101` também não retornaram. Após encerrar pytest, repeti `docker ps` somente de leitura e ele continuou sem responder por mais de 20 segundos. Enviei interrupção ao pytest e encerrei apenas os clientes Docker de diagnóstico iniciados nesta sessão; não reiniciei Docker, container ou serviço compartilhado.
- O log parcial está fora do Git em `C:/codex-data/temp/pyp-backend-final-20261102.log`; o último marcador é `EE [ 68%]`. O SQLite operacional local `backend/markina-gallery.db` permaneceu com 3.407.872 bytes e timestamp `2026-11-01T18:54:25Z`; a rodada usou o arquivo temporário acima.
- **Task 4.4 continua aberta.** Os resultados focados já registrados nesta validação permanecem válidos, mas não substituem a suíte completa. Retomar quando o Docker Desktop e o PostgreSQL sintético responderem a consultas somente de leitura: obter os tracebacks dos dois erros, concluir `backend/tests`, classificar skips e confirmar o teste PostgreSQL de reset/limpeza antes de marcar a task. Nenhuma alteração remota foi feita.

## Testes focados de segurança — 02/11/2026

- Uma primeira execução agrupou módulos de auth multi-tenant usando um único SQLite no `PHOTOGRAPHER_TEST_DATABASE_URL`: **93 passaram, 2 foram ignorados, 47 erros e 1 falha**. Os erros ocorreram em setup por colisão da fixture `admin@example.test` entre módulos (`UNIQUE admin_user.email`); o caso falho foi `test_instalacao_sem_conta_nao_escolhe_fallback`. Como a fixture desses módulos espera schema PostgreSQL isolado, esse resultado não é evidência de defeito de produto nem de aprovação dos testes multi-tenant; ele foi excluído do resultado focado.
- Repeti os módulos independentes de segurança em SQLite novo, sem `PHOTOGRAPHER_TEST_DATABASE_URL`: `test_admin_security.py`, `test_auth.py`, `test_otp_privacy.py`, `test_totp_crypto.py`, `test_totp_verification.py`, `test_totp_persistence.py`, `test_totp_migration.py`, `test_facial_crypto.py`, `test_facial_crypto_context.py` e `test_facial_security.py`. Resultado: **83 passaram, 2 ignorados, 50 avisos em 414,99 s**. Os dois skips de `test_totp_migration.py` exigem PostgreSQL descartável; não foram substituídos por SQLite.
- O teste focado usou `DATABASE_URL=sqlite:///C:/codex-data/temp/pyp-security-core-20261102/app.sqlite` e `--basetemp=C:/codex-data/temp/pyp-security-core-20261102/pytest`. Não acessou banco de produção nem dependeu do container PostgreSQL local indisponível. Os avisos incluem depreciações FastAPI/SQLite e ciclo de FKs em fixtures.
- Naquele checkpoint, a bateria SQLite não cobria isolamento tenant-versus-tenant nem migrations/concorrência PostgreSQL de TOTP. A suíte ampla concluída abaixo cobre os contratos tenant com o PostgreSQL sintético; os casos PostgreSQL específicos de TOTP têm evidência própria em `openspec/changes/protect-admin-totp-secrets/validation.md` (8 testes de migration e 2 de concorrência aprovados). A execução ampla abaixo substitui o resultado incompleto anterior para a task 4.4.

## Suíte backend ampla e reset PostgreSQL — 02/11/2026 (checkpoint atualizado)

Este checkpoint substitui o status incompleto da tentativa que parou em 68%. A execução anterior permanece registrada como histórico; a suíte abaixo concluiu integralmente.

- Comando: `.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short -r a --basetemp=C:/codex-data/temp/pyp-backend-resume-pytest-20261102`. `DATABASE_URL` apontou para SQLite temporário exclusivo em `C:/codex-data/temp/pyp-backend-resume-20261102/app.sqlite`; `PHOTOGRAPHER_TEST_DATABASE_URL` apontou para PostgreSQL 17.11 sintético e exclusivo em `127.0.0.1:15470/pyp_photographer_test`.
- Resultado: **1.860 passed, 32 skipped, 671 warnings, 0 failures** em **7.872,73 s (2h11m12s)**; código de saída 0. Os skips foram classificados no relatório pytest: 28 casos protegidos por variáveis/instâncias PostgreSQL específicas ou por validação de locks, 3 casos de symlink sem permissão no Windows e 1 jornada opt-in que exige PostgreSQL, build Next e Edge/Playwright. Nenhum skip foi contado como aprovado.
- Nenhum endereço de banco de produção foi configurado. O PostgreSQL usado foi o container local temporário `pyp-backend-suite-20261102`, imagem `postgres:17.11-alpine`, bind somente em `127.0.0.1:15470` e armazenamento em `tmpfs`. O teste usou dados sintéticos; o banco SQLite operacional do worktree não foi o destino da execução.
- Repetição focada: `test_tenant_owner_reset.py` e `test_homolog_cleanup.py` com `DATABASE_URL`, `PHOTOGRAPHER_TEST_DATABASE_URL` e `TEST_POSTGRES_DATABASE_URL` apontando para o mesmo PostgreSQL sintético dedicado. Resultado: **31 passed, 2 skipped, 0 failures** em **101 s**. O caminho de limpeza PostgreSQL executou; o reset preservou pacote/carteira do proprietário, recusou histórico de compra e ledger sem apagar evidências, e as rotinas de limpeza preservaram tabelas financeiras classificadas como protegidas. Os dois skips foram a ramificação que exige banco não PostgreSQL e a verificação de symlink indisponível neste Windows.
- A primeira repetição focada expôs uma divergência da própria fixture: o teste alterava `APP_ENV` para `homolog`, mas mantinha `ADMIN_TOTP_SECRET_ENV=test`, fazendo o cofre TOTP sintético falhar fechado antes do reset. A fixture agora define também `ADMIN_TOTP_SECRET_ENV=homolog`; a repetição integral dos dois módulos passou. Não houve falha no código de reset nem relaxamento da validação criptográfica.
- Logs e temporários ficaram fora do Git: `C:/codex-data/temp/pyp-backend-resume-20261102.log`, `C:/codex-data/temp/pyp-backend-resume-pytest-20261102/`, `C:/codex-data/temp/pyp-reset-focused-rerun-20261102.log` e `C:/codex-data/temp/pyp-reset-focused-pytest-rerun-20261102/`.
- As tasks 4.2 e 4.4 estão concluídas com esta evidência. Em 02/11/2026, o proprietário aceitou os limites de simulação externa registrados em `external-validation-results.md`. Nenhum banco remoto foi usado pelos testes; a inspeção de produção nesta sessão foi somente leitura de configuração e metadados agregados, sem leitura de linhas de clientes. Não houve alteração, migration ou publicação em homologação/produção.

## Proteção de downgrade financeiro — 14/11/2026

- A revisão estática encontrou que o downgrade da migration 0095 removia `mercadopago_credit_purchase` e `mercadopago_credit_purchase_event` sem verificar dados, apesar de esses registros serem snapshots e trilha financeira append-only.
- O downgrade agora exige PostgreSQL, bloqueia as duas tabelas contra escrita concorrente e recusa antes de remover objetos se qualquer uma contiver linhas. A especificação ganhou o cenário correspondente. Foi adicionada regressão PostgreSQL que aplica 0090→0095 em schema sintético, cria uma compra preparada com evento e comprova a recusa, versão Alembic e preservação das linhas.
- Ruff nos dois arquivos Python e `py_compile` passaram; OpenSpec strict validou a change. Um smoke isolado com conexão PostgreSQL simulada confirmou que o downgrade faz lock e checagem antes de qualquer drop; os trechos alterados não têm whitespace final. `git diff --check` passou, com avisos LF/CRLF em arquivos rastreados sem relação com esta correção.
- A regressão PostgreSQL real ainda não foi executada: `PHOTOGRAPHER_TEST_DATABASE_URL` não está configurada e o PostgreSQL sintético isolado esperado em `127.0.0.1:15470` não está disponível. Nenhum banco foi iniciado ou alterado; a task 4.5 permanece aberta.

## Fallback de identidade no checkout — 14/11/2026

- A revisão confirmou que `prepare` permite a conta legada sem signup, enquanto `/admin/onboarding/checkout-identity` pode responder 409 quando o perfil ainda não existe. A tela antes ocultava os campos de endereço e permanecia carregando, bloqueando a compra mesmo quando o pagador podia fornecer os dados para essa transação.
- O checkout agora preenche campos a partir do perfil quando disponível; em resposta não válida, erro de leitura ou perfil ausente, oferece endereço manual para a compra atual e informa que nada será gravado no perfil. O gate de onboarding de novos cadastros continua no backend antes de preparar a compra.
- Regressão `credit-purchase-checkout.test.tsx`: **4 passed**. ESLint focalizado nos dois arquivos alterados passou; `npx tsc --noEmit` passou. Nenhuma chamada a endpoint de gravação de perfil foi adicionada.
- A página conserva a mesma chave de idempotência ao repetir uma preparação após erro HTTP e só gera outra após sucesso. Se a consulta de carteira após confirmação/recuperação falhar, o pedido continua visível, métricas e histórico antigos são ocultados e o botão permite tentar atualizar de novo; compras novas ficam pausadas até a carteira atualizar.

- `credit-purchase-checkout.test.tsx` + `page.test.tsx`: **11 passed** após esses ajustes. ESLint focalizado nos quatro arquivos alterados e `npx tsc --noEmit` passaram.
- Execução de todo o diretório `app/admin/credits`: **37 passed em seis arquivos**; OpenSpec strict validou novamente `add-mercadopago-credit-purchases`. O teste verifica duas tentativas de preparo com a mesma chave, confirmação preservada durante falha do refresh, ocultação do saldo/histórico antigo e sucesso no botão de nova consulta.

## Limite da reconciliação manual — 14/11/2026

- A revisão encontrou que `POST /admin/credits/purchases/{purchase_id}/reconcile` não aplicava limite de chamadas, embora pudesse consultar a Order no Mercado Pago. A rota agora usa o limite comum por administrador/IP antes de executar a reconciliação.
- `tests/test_mercadopago_credit_purchases.py::test_reconciliacao_manual_de_compra_de_creditos_tem_rate_limit` confirma cinco chamadas aceitas e a sexta recusada com HTTP 429. A compra da regressão permanece em `prepared`, portanto nenhuma consulta financeira externa ocorre.
- `python -m pytest tests/test_mercadopago_credit_purchases.py -q`: **29 passed**, 6 avisos FastAPI de depreciação. Ruff focal passou após a organização automática de um import. A primeira coleta pelo Python global não tinha `mercadopago`; o teste foi repetido com `backend/.venv` instalado por `requirements.txt`.

## Gate do histórico de créditos no reset de homolog — 15/11/2026

- A revisão da rotina `homolog_cleanup.execute` encontrou que `has_credit_wallet_history` detectava ledger, operações, eventos e alocações, mas não era chamado. O reset agora recusa depois dos locks e antes de resolver/alterar mídia quando qualquer registro desse histórico existe, conforme a regra de preservação desta change.
- A regressão `test_execute_blocks_credit_wallet_history_before_media_or_deletes` comprova a recusa antes de consultar raízes ou fazer commit; `backend/tests/test_homolog_cleanup.py`: **18 passed, 1 skipped**. Ruff dos dois arquivos alterados passou. A execução não chamou a rotina de limpeza nem alterou banco operacional ou mídia.
- O teste PostgreSQL dedicado não pôde ser executado porque `127.0.0.1:15470` está sem listener; a evidência desta correção cobre o fluxo de recusa com locks PostgreSQL simulados. A integração real continua como gate pendente.

## Prova PostgreSQL do downgrade financeiro — 15/11/2026

- Autorização expressa recebida para iniciar o ambiente local de testes. Docker confirmado em `desktop-linux`; PostgreSQL 17.11 criado exclusivamente para os gates em `127.0.0.1:15470/pyp_photographer_test`, tmpfs 1 GiB e sem mounts persistentes. Recursos preexistentes foram preservados.
- A primeira prova revelou fixture incompatível: o ORM atual inseria `Tenant.lifecycle` em schema 0095. A regressão agora reflete as tabelas históricas e insere uma compra preparada e evento sem depender dos gates atuais; os ajustes seguintes completaram os valores históricos obrigatórios sem relaxar constraints.
- `test_tenant_credit_purchase_postgres.py::test_downgrade_refuses_to_drop_credit_purchase_history`: **1 passed em 39,44 s**, sem skips. A recusa preservou a versão Alembic 0095, a compra e seu evento. Ruff passou. Relatório externo: `C:/codex-data/local-review/prepush-credit-downgrade-final-20261115.xml`. Task 4.5 concluída; nenhum banco operacional foi migrado.

## Limpeza bloqueada por ledger — PostgreSQL real — 15/11/2026

`test_homolog_cleanup_retained_history_postgres.py`: **2 passed em 76,17 s**, sem skips, no banco descartável 15470. Os casos de histórico de encerramento e ledger de créditos recusaram `execute` antes de resolver mídia; inserção concorrente foi bloqueada com SQLSTATE 55P03 até rollback, e registros foram preservados. O fixture foi atualizado de 0124 para a head real de migrations, pois o ORM corrente contém marcadores posteriores. A prova de ledger cobre a chamada adicionada a `has_credit_wallet_history`. JUnit externo `C:/codex-data/local-review/prepush-cleanup-locks-20261115.xml`; nenhum banco operacional ou arquivo de mídia foi removido.

### Snapshot, ledger e confirmação concorrente em schema migrado — 15/11/2026

Os três casos ainda não executados de `test_tenant_credit_purchase_postgres.py` passaram: upgrade preserva proprietário/backfill das carteiras; constraints isolam conta recebedora, snapshot e histórico append-only; duas confirmações simultâneas resultam em um único crédito/evento. A execução conjunta com a disputa de reserva de recuperação concluiu **4 passed, 1 deselected**, em 55,24 s; o caso de downgrade 0095, já aprovado, foi deliberadamente excluído desta repetição. JUnit `C:/codex-data/local-review/prepush-credit-races-postgres-20261115.xml`. Fixtures em schemas descartáveis do PostgreSQL 17.11 `127.0.0.1:15470/pyp_photographer_test`, após autorização local. Nenhuma Order/pagamento ou chamada externa criada; prova sintética não fecha a validação real do provedor.
