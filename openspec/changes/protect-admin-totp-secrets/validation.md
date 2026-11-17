# Validação e limites

## Custódia em arquivo privado — 16/11/2026

`scripts/admin_totp_custody.py` reutiliza o cipher TOTP e as primitivas POSIX privadas do emissor. Quatro testes passaram em container Linux/Python3.10: modos/proprietário/symlinks/hardlinks, configuração e JSON duplicado, ambiente divergente com recusa antes do consumidor, recuperação após remoção do arquivo fonte. No Windows os quatro casos são explicitamente skipped por dependerem de POSIX; isso não foi contado como validação Linux. Ruff e OpenSpec estrito passaram.

Ensaio SSH independente executou o helper no host e entregou as variáveis por ambiente ao cliente Docker, sem valores em argv. O container intermediário isolado em rede none cifrou uma fixture sintética; o keyring foi copiado para a memória do processo Windows, removido da origem, transferido de volta para diretório privado e recuperou a mesma fixture. Recibo sanitizado `totp-file-custody-proof.json` no diretório externo de revisão. A cópia de recuperação deste ensaio é transitória; custódia real externa durável/offline e ativação produtiva continuam pendentes. Nenhuma chave real foi criada e nenhum container produtivo foi substituído.

A primeira tentativa foi recusada porque o caminho de revisão tinha um ancestral pertencente ao usuário de aplicação. O ensaio passou em raiz privada sob `/run`; a localização proposta para uso durável é `/etc/pyp-totp`, root:root e0700, com arquivo0400/0600. A primeira chamada Docker usava imagem anterior sem o módulo cipher e foi corrigida para a imagem intermediária já inventariada. Esses ajustes foram limitados ao harness.

Revisão proporcional reutilizou `_private_directory`/`_read` e `TotpSecretCipher`, sem duplicar validações de filesystem ou algoritmo. O helper mantém o contrato de ambiente atual; não houve refatoração de código alheio.

## Base e segurança operacional

- Base da worktree: `origin/main=6af538ecd5c46da7691fa973c33869f263945a25`, branch isolada `feature/pickyourpic-saas-mainline`.
- Produção consultada somente para leitura; API/worker e bancos produtivos não receberam migration, write, segredo, teste autenticado, restart ou deploy.
- Todo PostgreSQL desta validação é o container descartável `pyp-saas-isolated-pg-20261031`, publicado somente em loopback e sem volume persistente. As tabelas e contas de rotação/migration contêm apenas fixtures sintéticas.
- Nenhum segredo real, valor de `.env`, código TOTP, código de recuperação ou dado de cliente foi incluído neste artefato.

## Validações concluídas

- `tests/test_totp_crypto.py`, persistência, migração e verificação TOTP, fluxo de códigos e regressões de autenticação administrativa: 13 passed; Ruff focalizado aprovado.
- Seed, provisionamento e emissão de códigos foram reforçados com inspeção do conteúdo bruto persistido: `test_tenant_foundation::test_seed_vincula_admin_e_preserva_credenciais` passou; os dois testes de seed/provisionamento selecionados passaram. O banco continha envelope `totp:v1` e não continha o fator sintético em claro.
- Regressões selecionadas da suíte ampla: 33 passaram na primeira repetição focada; os cinco casos restantes passaram usando `https://testserver`, compatível com o cookie `Secure` de `APP_ENV=staging`. A causa era o cliente HTTP do teste em HTTP; nenhuma autorização foi relaxada.
- Checkpoint focalizado após reforçar rollback da regeneração: 12 passed em crypto, verificação, persistência, recuperação hash-only, autenticação senha+TOTP e provisionamento/seed; teste isolado de recuperação adicional: 1 passed.
- `tests/test_totp_migration.py`: 4 passed com PostgreSQL sintético, incluindo failure injection. A migration recusou fator vazio e o banco permaneceu em `20261026_0090`, com coluna `totp_last_used_step` ausente, `totp_secret` em 128 caracteres e os dois valores de origem intactos. O banco temporário de falha foi descartado pelo próprio fixture.
- Checkpoint após corrigir a compatibilidade expand/contract: `test_totp_crypto.py`, persistência, migration, verificação, concorrência PostgreSQL e login dual-write: 20 passed. O PostgreSQL sintético percorreu base vazia → `0092` → `0093`, simulou ORM legado lendo e atualizando `totp_secret`, verificou reconciliação do fator, contract, downgrade até `0090` e falha atômica sem alteração de schema/valores.
- Regressões de auth/admin/tenant/provisionamento: 65 passed em 282,66 s. Login senha+TOTP funciona com dual-write desligado nos fluxos existentes e com dual-write ligado no cenário de escritor legado.
- PostgreSQL concurrency: replay do mesmo passo TOTP e consumo concorrente do mesmo código de recuperação: 2 passed; cada caso aceitou no máximo uma sessão.
- PostgreSQL Alembic: base `0090` → `0093`, fator sintético preservado em envelope com chave/contexto; downgrade restaurou plaintext antes do rollback e novo upgrade percorreu a cadeia. Base isolada vazia também chegou ao head `20261031_0093`. Os testes executaram após acrescentar o lock de tabela do contract.
- CLI real contra PostgreSQL sintético: dry-run não alterou registros, apply com confirmação recifrou registros, novo dry-run indicou zero pendências e decrypt verificou os fatores; retirar uma chave ainda referenciada recusou a rotação.
- A tabela de recuperação foi classificada como dado de segurança administrativo preservado, não operacional, em `app/homolog_cleanup.py`; `tests/test_homolog_cleanup.py` passou na suíte backend integral corrigida.
- Frontend: `security-panel.test.tsx` 4/4 após cobrir recuperação da UI quando a requisição falha; suíte completa anterior a esse teste 556/556 em 65 arquivos. `tsc --noEmit` e build Next passaram após a alteração final. ESLint frontend terminou com 0 erros e 36 warnings preexistentes no checkout.
- Docker Compose `config --quiet` passou sem iniciar serviços.
- `openspec validate protect-admin-totp-secrets --strict --json` e `reconcile-production-runtime-drift --strict --json`: passaram.
- Ruff focalizado nas mudanças TOTP, regressões e migrations novas passou. Ruff global de `migrations/versions` ainda aponta 16 alertas em migrations históricas não alteradas; não foram reformatadas.

## Execuções amplas e pendências remanescentes

- Suíte integral backend com `APP_ENV=development`, SQLite temporário e segredos sintéticos: **1.731 passed, 86 skipped, zero falhas e 671 warnings em 5.195,22 s**. Essa rodada antecedeu o último ajuste isolado da CLI de rotação; após o ajuste, o módulo `tests/test_totp_migration.py` concluiu com **8 passed em 36,76 s**, inclusive a regressão de dry-run em janela dual-write e os cenários PostgreSQL sintéticos. Os 86 skips não foram classificados individualmente; R13-004 permanece parcial junto aos gates integrados de produto.
- A primeira tentativa pós-mudança usou `APP_ENV=test` sem toda a configuração sintética exigida: resultou em 77 failed/379 errors, concentrados em ausência/divergência de configuração (chaves de capacidades, fingerprint, keyrings de TOTP/integrações). Essa execução não é evidência de regressão de produto. `tests/conftest.py` passou a definir valores sintéticos por finalidade e o teste de chave ausente remove a variável explicitamente. Com ambiente consistente, 7 cenários representativos passaram e a bateria focada de auth/crypto/migration/PostgreSQL/regressões tenant passou: **94 passed em 327,41 s**.
- A bateria focada passou após o lock explícito: upgrade/contract/downgrade com ORM legado, replay TOTP e consumo concorrente de código de recuperação em PostgreSQL sintético, persistência/crypto, login e provisionamento.
- Após o último ajuste, Ruff focalizado passou; `openspec validate protect-admin-totp-secrets --strict --json` passou; `alembic heads` reportou somente `20261031_0093 (head)`; `git diff --check` passou, com aviso de conversão LF→CRLF em `backend/tests/test_admin_security.py`.
- Revisão final do diff TOTP concluída. Não há `.env` ou arquivo de credenciais no conjunto alterado; a varredura encontrou apenas tokens/valores sintéticos usados nos testes. `requirements.json` parseia com 694 itens e as contagens declaradas coincidem com os estados. A matriz foi mantida sem promover R13-004 enquanto os 86 skips e os gates integrados continuam pendentes.

## Bloqueios e compatibilidade

- A migration local `0091` agora preserva a coluna legada e grava envelope em coluna separada; `0093` reconcilia a última escrita legada válida e limpa plaintext apenas com dual-write desligado. PostgreSQL isolado comprovou leitura/escrita com um ORM legado, login com o runtime novo, contract e downgrade. Essa evidência é sintética e não substitui inventário/ensaio do runtime operacional.

- A API de produção observada em snapshot `74f61300…` mapeia `AdminUser.totp_secret` como `String(128)` e passa o valor diretamente ao PyOTP; a expansão preserva esse contrato. O worker `c1944189…` hidrata `AdminUser`, mas não foi encontrado acesso direto a `.totp_secret`; ele ainda requer prova no código/runtime correspondente. Não executar migration remota.
- A sequência externa continua sem inventário completo de processos/instâncias, backup restaurável, reconciliação de todos os consumidores e autorização. Nenhum deploy, migration remota, alteração de keyring ou teste autenticado de produção ocorreu.
- A API e o worker de produção estão em versões distintas da base `main`; a divergência do worker inclui `auth.py` e `main.py`. Nenhuma chave externa real, backup de produção, estado de conta ou comportamento autenticado real foi inspecionado.
- `docs/OPERACAO-SEGREDO-TOTP.md` registra o pacote local API/worker, a sequência expand/contract, rollback e plano de impacto zero. Isso completa o artefato local de 3.3, mas não comprova os binários/processos produtivos nem autoriza ações externas. A task 3.4 continua aguardando revisão humana antes de sincronizar specs e arquivar.

## Rechecagem da postura de produção somente leitura — 02/11/2026

- A API, o worker e o PostgreSQL estavam saudáveis no momento da consulta SSH read-only. A API reportava `APP_ENV=production`; o nome configurado do banco é `markina_gallery_homolog`, divergência de nomenclatura que não permite inferir o ambiente dos dados. O container da API usa a imagem `sha256:0d14e294a7581f0f863e19a030f158ef2b59c6e409cf0c4a763124906459ef6f`, sem label `org.opencontainers.image.revision`; portanto, o commit exato dessa imagem não pôde ser provado pelo label.
- O código presente na imagem da API não contém `app/totp_crypto.py`. `provision_photographer.py` grava o segredo normalizado diretamente em `AdminUser.totp_secret`, e `main.py` passa esse valor diretamente a `pyotp.TOTP`. O schema confirma `admin_user.totp_secret` como `character varying` e não apresenta coluna `totp_secret_envelope`. A cifragem TOTP AES-GCM validada nesta change permanece somente no código local; ela não está ativa no runtime observado.
- O PostgreSQL respondeu `SHOW ssl = off`. Sessões atuais da API/consumidores a partir dos endereços Docker `172.21.0.7`, `.8` e `.9` reportaram `pg_stat_ssl.ssl=false`. O banco não tem porta publicada no host, mas participa da bridge `markina-gallery_internal` com `internal=false`, compartilhada por API, worker, web, Nginx, workers/serviços Evolution e Redis.
- O papel `markina_gallery_homolog` apresentou `rolsuper`, `rolcreatedb`, `rolcreaterole`, `rolreplication` e `rolbypassrls` verdadeiros. A contagem agregada de tabelas públicas com RLS habilitado/forçado foi `0/0`; o isolamento tenant observado depende das verificações da aplicação, sem uma barreira RLS no banco. Nenhum conteúdo de tabela ou registro de cliente foi consultado.
- Os processos API (`uvicorn`) e worker (`python`) aparecem como `root`. As configurações desses containers mostram `ReadOnlyRootfs=false`, sem `CapDrop` e sem `SecurityOpt`. A coluna de senha é `password_hash`; as credenciais Mercado Pago usam colunas `access_token_envelope` e `webhook_secret_envelope` JSON, o que demonstra proteção seletiva de segredos. Isso não equivale a cifragem de todas as colunas nem prova cifragem do volume.
- A cifragem de dados em repouso no volume gerenciado pelo provedor OCI não foi confirmada nem negada por esta inspeção do guest. Não foi possível concluir que o banco/volume inteiro esteja cifrado em repouso.
- Esta inspeção foi limitada a estado/configuração de containers, sessões e metadados agregados. Não leu valores de segredos ou linhas de clientes e não alterou produção: sem migration, escrita, restart, deploy ou ajuste de rede/credenciais. Os achados são riscos operacionais para priorizar em change/release própria; não autorizam rollout da implementação local.

## Reexecução PostgreSQL dos dois gates históricos — 15/11/2026

Com a autorização vigente para iniciar o ambiente local de testes, foi criado `pyp-totp-gates-20261115` no Docker `desktop-linux`, PostgreSQL 17.11 em `127.0.0.1:53005/totp_migration_test`, tmpfs 512 MiB, sem mounts persistentes e com credenciais sintéticas fora do Git. A porta/database rígidos dos testes foram preservados; não houve redirecionamento do guard.

`test_totp_migration.py -k postgresql`: **2 passed, 6 deselected em 108,04 s**, sem skips. A primeira prova confirma rollback transacional de schema e todas as linhas quando há segredo malformado; a segunda confirma ORM legado durante expand, reconciliação da escrita legada e reversibilidade do contract. JUnit `C:/codex-data/local-review/prepush-totp-migration-postgres-20261115.xml`. Esses dois gates antes ignorados por ambiente estão aprovados. Nenhum segredo ou banco operacional foi lido/alterado.

### Replay concorrente em PostgreSQL — 15/11/2026

Com o início local autorizado pelo proprietário, `test_totp_postgres_concurrency.py` concluiu **3 passed, zero skips/falhas**, em 30,09 s. Os casos disputam o mesmo passo TOTP, o mesmo código de recuperação e o mesmo link de reset do website + TOTP; cada um permite somente uma conclusão/sessão. PostgreSQL 17.11 sintético em loopback `53005/totp_migration_test`, schemas próprios removidos pelas fixtures; nenhum autenticador, e-mail ou conta de produção. JUnit: `C:/codex-data/local-review/prepush-totp-replay-postgres-20261115.xml`. Sem alteração funcional neste bloco; não foi executada a suíte backend completa.

## Pacote intermediário para o rollout integrado — 16/11/2026

O preparador `scripts/prepare_admin_totp_compatibility.py` opera somente em arquivos locais: exige hash do módulo legado, recusa origem/shape divergentes e diretório existente, preserva trechos não relacionados e emite módulo, cipher do candidato, Dockerfile e manifesto. Não executa Docker/rede/banco/keyring. A manutenção ficou limitada ao artefato temporário necessário à sequência expand/contract; nenhuma limpeza da aplicação foi feita.

`python -m pytest scripts/test_prepare_admin_totp_compatibility.py -q`: **8 passed**. A prova cobre preservação de fonte/LF/CRLF, recusa de shape ambíguo, hash divergente sem escrita, preservação de saída existente, dual-write com atualização legada, continuidade do mesmo fator após contract e envelope inválido. Ruff dos dois scripts e OpenSpec estrito passaram. JUnit local `C:/codex-data/local-review/saas-release-review-20261115/totp-compatibility-package.xml`.

A fonte realmente lida da API observada tem SHA-256 `e3115bd5b0c49148470317a22bd7433a0096ae7f342f202e7068de1a83ea2c8a`; o módulo gerado tem `453eb749aa3ffca8aa8e5cc77470af8e66522e4d1cc80f11c654d7299086219c`. Imagem de base `sha256:6e732610932d5e7eb01c1fbed5ddbc7a1f4b05a39da9de8179c0ed0ab8375aea`; imagem intermediária de ensaio `sha256:61de18af03fcb978ec7f6c5ef4fd3fb81a5f75d84fb966d87ccdebd71df323c6`. CMD e Entrypoint conferidos por valor. A primeira conferência tentou acessar um campo Entrypoint ausente; a verificação foi corrigida para tratar ausência como None, sem novo build nem mudança de runtime.

O ensaio usou exclusivamente o PostgreSQL restaurado `saas_restore_review` em namespace de rede `none`, já migrado a0126, e o keyring exclusivo dessa cópia. O módulo legado transformado carregou a conta existente e verificou seu TOTP sem plaintext, e cifrou uma inserção sintética revertida em rollback; contagem de contas permaneceu igual. APP_ENVproduction e facialtrue foram preservados no processo de ensaio. Recibo restrito remoto `saas-preflight-20261116-24f2fba2/totp-compatibility-api-proof.json`.

Isso não comprova startup HTTP completo, troca de tráfego, drenagem, compatibilidade de todos os workers ou indisponibilidade zero. Produção continua com seus serviços/imagens atuais e schema0090; nenhum keyring TOTP produtivo foi criado nem implantado. O worker de prévias inventariado segue APP_ENVstaging, não foi alterado e exige reconciliação de consumidores antes do corte.
