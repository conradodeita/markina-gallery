# Validação — conexão segura com Google Drive

## Evidência local — 03/11/2026

- `backend/tests/test_google_drive_oauth.py`: **29 passed** após a correção de revogação descrita abaixo. Casos cobrem bloqueio de rede real fora de produção, configuração/redirect URI, callback sintético com state de uso único/PKCE e refresh token cifrado, preservação de conexão sem refresh token, revogação sintética com limpeza de envelope, reautenticação owner, limite de tentativas, negação de outro tenant, consulta de quota por transporte sintético, seleção mínima de campos, quota parcial desconhecida e respostas 400/401/403/429/503 de quota, troca de código e revogação sem revelar corpo do provedor. O adapter repete apenas um GET idempotente em 429/5xx; POST de token não é repetido.
- `backend/tests/test_tenant_ownership_schema.py::test_google_drive_tables_have_explicit_global_and_shared_ownership`: **1 passed** em SQLite. Suite combinada de ownership/migration, executada sem URL PostgreSQL: **24 passed, 19 skipped**; skips são casos exclusivos de PostgreSQL.
- Ruff direcionado nos módulos OAuth, autenticação, schema de ownership, migration 0098, testes e scripts de preservação: **All checks passed**.
- `openspec validate add-google-drive-storage-foundation --strict`: **valid**.
- Callback candidato foi comparado à configuração local: Nginx remove `/api/` no proxy e o FastAPI monta `/admin/platform/drive/oauth/callback`. Isso não comprova o roteamento atualmente ativo em produção.
- `git diff --check`: sem erro; houve apenas aviso de conversão de line ending em arquivo preexistente `backend/tests/test_admin_security.py`.
- Execução combinada PostgreSQL anterior à correção do catálogo: **41 passed, 1 failed**. A falha identificou que a expectativa do teste não incluía `google_drive_oauth_attempt` (compartilhada com `tenant_id`) e `google_drive_connection` (global do owner com `tenant_id`). A expectativa foi corrigida. A repetição direta não autenticou no serviço isolado pela URL reconstruída; portanto a correção do catálogo ainda requer validação PostgreSQL por ambiente configurado corretamente. O ambiente correto não foi alterado nem inspecionado para recuperar credenciais.
- A primeira coleta com Python global falhou porque o ambiente não tinha a dependência `mercadopago`; a repetição pelo `backend/.venv` executou os testes OAuth normalmente. Essa falha foi do interpretador selecionado, não do módulo OAuth.

## Upload resumable sintético — 06/11/2026

- `backend/.venv/Scripts/python.exe -m pytest tests/test_google_drive_storage.py tests/test_google_drive_oauth.py -q`: **45 passed**, 6 avisos de depreciação FastAPI preexistentes. Cobertura inclui bloqueio fora de produção, destino ausente, host/path inseguro de sessão, chunks alinhados e Range exato, timeout limitado, nenhum retry PUT, metadata/checksum divergentes, stream/tamanho inválidos e recibo sem URL de sessão/link.
- O fake transport responde a todos os pedidos; nenhuma conexão HTTP externa ou conta Google foi usada. O teste define `APP_ENV=production` somente para o helper e injeta transporte sintético.
- `python -m ruff check app/google_drive_oauth.py app/google_drive_storage.py tests/test_google_drive_storage.py`: **All checks passed**. `compileall` dos mesmos arquivos passou.
- `openspec validate add-google-drive-storage-foundation --strict`, `add-gallery-media-archive --strict`, `add-platform-backup-recovery --strict` e `add-platform-owner-console --strict`: **valid**. `git diff --check` sem erros; avisos de conversão CRLF em `backend/tests/test_admin_security.py` e `frontend/app/globals.css` são preexistentes.
- Python global inicialmente não coletou a suíte por falta de `mercadopago`; o rerun final usou o ambiente existente `backend/.venv`, sem instalar dependências.
- Não há caller/rota, destino autorizado, consentimento Drive ou validação real. Task 3.1 continua aberta e não houve upload ou alteração de serviço/dados remotos.

## Correção local posterior — revogação HTTP 400

A [documentação oficial de revogação OAuth do Google](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke) classifica HTTP 200 como sucesso e HTTP 400 como erro. O código anterior aceitava ambos, contrariando o cenário OpenSpec que preserva a conexão em erro. O caso sintético `test_revoke_provider_errors_preserve_connection_and_are_sanitized[400]` falhou antes da correção: a rota não lançou erro e marcou a conexão como revogada. Agora somente HTTP 200 permite limpar o envelope. O mesmo caso e a suíte inteira passaram: **29 passed** em 210,19 s, com 6 avisos deprecatórios preexistentes; nenhum acesso Google real. Ruff direcionado: **All checks passed**; OpenSpec strict: **valid**. Nenhuma alteração de migration, schema ou secret foi feita nesta correção.

## Limites da validação

Atualização operacional posterior: DNS e TLS do host raiz foram concluídos e validados separadamente, conforme `operations.md`. O domínio responde HTTP 301/HTTPS 404 reservado; `markina` permaneceu 200, NPM `nginx -t` passou. Certificado público SAN/validade foram conferidos; chaves privadas não foram consultadas. Não houve deploy, migration, configuração de credencial OAuth, consentimento ou chamada Drive real. A consulta somente-leitura do schema remoto retornou 0090; riscos da cadeia 0091–0098 e da sessão entre hosts constam em `release-readiness.md`.

- Os transportes são sintéticos. O proprietário criou um cliente OAuth Web no Console e o reportou como Enabled; o executor não leu o JSON nem consultou ID/secret.
- Não houve autorização de Drive, observação real de quota, upload, leitura ou revogação Google, nem publicação/deploy. O client secret não foi configurado no servidor.
- OAuth real e chamadas Drive permanecem limitados por `APP_ENV=production`. A validação real depende da etapa de produção com aprovação operacional específica, inventário de callback/portas, impacto zero e arquivo sintético.
- A cobertura local especificada em 2.3 passou com adapters sintéticos: callback e revogação válidos, falha sem refresh token, erros do provedor, redaction, quota, estado desconectado, limite de senha/TOTP e acesso de tenant fotógrafo negado. O teste PostgreSQL de catálogo ainda requer repetição com ambiente de teste corretamente provisionado. Task 3.1 está intencionalmente pendente de autorização operacional e teste de produção.

## Pré-checagem do callback público — 03/11/2026

### Atualização posterior — DNS salvo às 22:04 (GMT-3)

Inventário SSH e plano de impacto registrados em `operations.md`: NPM compartilhado atende 80/443; o host existente de `markina` usa alias do nginx do produto; a API publicada não contém `app.google_drive_oauth`. Depois desse inventário, o certificado npm-4 e o host 404 reservado foram criados exclusivamente para o domínio raiz. A necessidade de release da aplicação permanece como bloqueio de 3.1.

- O proprietário confirmou o mesmo Oracle para o site raiz. A zona avançada no Registro.br mostrava somente o A de `markina.pickyourpic.com.br` para `132.145.193.169`; foi acrescentado e salvo o A de `pickyourpic.com.br` para o mesmo IP, preservando o existente. O painel exibiu `Zona DNS atualizada com sucesso!` e, ao reabrir a zona, mostrou os dois registros e o botão de salvar desabilitado.
- Consulta posterior `https://dns.google/resolve?name=pickyourpic.com.br&type=A`: `Status=0`, `Answer` tipo A com `132.145.193.169`, TTL 3600. Resolve o bloqueio de ausência de DNS da pré-checagem anterior, sem garantir atualização em todos os resolvedores.
- Pré-checagem histórica HEAD, sem cookies nem parâmetros OAuth, com resolução direta do host raiz para esse IP: falha Schannel na negociação TLS (`SEC_E_ILLEGAL_MESSAGE`), sem contornar validação de certificado. Depois, o certificado e o host 404 raiz foram criados e a requisição HTTPS passou com TLS válido. HEAD em `https://markina.pickyourpic.com.br/` respondeu HTTP 200, OpenResty/Next.js.
- Nenhum firewall, deploy, migration, secret ou Google Drive real foi alterado nesta preparação. Estado atual: DNS e TLS do host raiz preparados; runtime OAuth publicado, secrets, consentimento e ensaio de produção continuam pendentes. As observações de ausência de A/AAAA abaixo são históricas.

- Host candidato: `pickyourpic.com.br`; callback local esperado: `/api/admin/platform/drive/oauth/callback`.
- As consultas A e AAAA ao Google Public DNS responderam sem seção `Answer` para o host raiz e com autoridade SOA. Evidência reproduzível: `https://dns.google/resolve?name=pickyourpic.com.br&type=A` e `https://dns.google/resolve?name=pickyourpic.com.br&type=AAAA`.
- Um GET HTTPS sem parâmetros OAuth ao callback falhou com `Could not resolve host` e `HTTP 000`. A requisição não chegou ao servidor; portanto, não prova comportamento do proxy nem da rota em produção. Não foram enviados cookies, state, código ou credenciais.
- Inventário versionado, não runtime: `docker/nginx/nginx.conf` escuta porta 80 no container e reescreve `/api/...` para `api:8000`; `docker/docker-compose.yml` publica `${MARKINA_GALLERY_PORT:-8080}:80`. Esses valores não confirmam a topologia de produção, cujo proxy público, IP/CNAME, imagem e portas não foram inspecionados.
- Bloqueio: o hostname público precisa resolver e encaminhar para o backend; o proprietário precisa confirmar a URI salva no cliente OAuth e o host de produção. Não adivinhar IP nem alterar DNS, proxy ou secrets.

## Preparação pendente para 3.1 — sequência histórica

1. Depois de o proprietário configurar o DNS no provedor autoritativo usando o destino correto da hospedagem, repetir somente uma consulta DNS e um GET sem parâmetros OAuth; interromper se houver redirecionamento inesperado, erro de certificado ou rota divergente.
2. Antes de qualquer fluxo real, levantar o deployment efetivo: subdomínio e TLS público, portas do proxy/API, imagem/SHA e schema, serviço/secret store específico, referência saudável de rollback e impacto em serviços compartilhados. O inventário de runtime ainda não existe neste registro.
3. Apresentar esse inventário e um plano de impacto zero ao proprietário e obter autorização operacional específica. Só então configurar `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, `GOOGLE_DRIVE_REDIRECT_URI` e verificar a chave `INTEGRATION_SECRET_*` sem registrar valores em artefatos.
4. Com autorização OAuth do proprietário, observar apenas quota/capabilities mínimas e executar o ensaio previsto com um arquivo sintético em destino de teste aprovado. Não usar fotos/clientes, criar links públicos, fazer arquivamento ou remover objeto. Qualquer limpeza posterior exige confirmação própria.

As tarefas 1.1 e 3.1 continuam abertas. O DNS e o TLS já foram preparados; encaminhamento do callback para aplicação publicada, custódia/configuração de segredo, consentimento e aprovação operacional permanecem gates externos. A indisponibilidade atual não autoriza completar essas tarefas por inferência. O estado operacional atualizado está em `operations.md` e `release-readiness.md`.
# Correção de capacidade do estado — 07/11/2026

O ORM usa agora `String(32)` e a migration aditiva `20261107_0108` amplia somente `google_drive_connection.state`, posterior à 0107. A revisão 0098 foi preservada. O downgrade recusa redução quando há valor maior que 16 caracteres; não reescreve estado ou envelope.

No PostgreSQL sintético existente (`desktop-linux`, container `pyp-subdomain-test-20261105`, loopback 15470, banco `pyp_photographer_test`, tmpfs), passaram **35 testes em 193,10 s**: migration 0108, cadeia real 0090→0108 com proprietário sintético, teste do console que antes falhava e suíte OAuth. Sem skips, sem chamadas Google, sem credencial real. A URL de teste foi configurada apenas na memória do processo a partir da credencial sintética existente, sem gravar `.env` ou imprimir valores.

Ruff dos arquivos afetados passou; Alembic tem head único `20261107_0108`; OpenSpec strict passou. Não há frontend afetado por esta correção. A revisão proporcional não identificou limpeza funcional segura necessária: foi alterada apenas a capacidade do campo e acrescentada prova PostgreSQL. Nenhuma migration foi aplicada à UI local 15472 nem a produção; os schemas exclusivos dos testes foram removidos pelas fixtures. A publicação ainda exige análise de lock/compatibilidade e autorização operacional, como as demais migrations.

### Estado de conexão/capacidade em PostgreSQL — 15/11/2026

Os dois casos de `test_tenant_drive_state_migration.py` passaram: preservação e recusa de downgrade com estado salvo, e cadeia real até0108 com proprietário sintético. JUnit `C:/codex-data/local-review/prepush-remaining-postgres-20261115.xml` (11aprovações; outros casos tiveram uma falha de fixture e um skip, resolvidos em relatórios separados). Somente PostgreSQL17.11 loopback15470/schema aleatório; nenhum OAuth, quota, upload ou conta Google real consultado.
