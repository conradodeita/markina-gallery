# Validação

Data da execução local: 2026-11-07.

## Compatibilidade de hostname e isolamento

- `backend/tests/test_tenant_host_reservation.py` e `backend/tests/test_tenant_hosts.py`: 24 testes passaram antes das mudanças no console; a suíte de reserva voltou a passar com o teste A/B de sessão acrescentado.
- Testes direcionados de sessão A/B, spoof de `X-Forwarded-Host`, links de compra/galeria, autenticação de compra em hosts diferentes, host desconhecido, worker após mudança do host, notificação e operador do console: **16 passaram**.
- `backend/tests/test_tenant_admin_auth.py::test_cookie_revalida_apos_login_sem_afetar_B` e `::test_senha_exige_TOTP_e_cookie_identifica_vinculo_proprio_A_B`: **5 passaram** depois de ajustar o helper de teste para fornecer `Response`, como exige a assinatura de `admin_password`.
- Cookie de administrador permanece `HttpOnly`, `Secure` fora de desenvolvimento e sem atributo `Domain`.

## Ativação no console

- A primeira execução sem `PHOTOGRAPHER_TEST_DATABASE_URL` pulou o teste DDL. O inventário posterior encontrou o container já existente `pyp-subdomain-test-20261105`, Docker `desktop-linux`, PostgreSQL `17.11-alpine`, saudável, exclusivamente em `127.0.0.1:15470/pyp_photographer_test`, dados em tmpfs e sem mounts persistentes. A credencial sintética foi usada somente na memória dos processos de teste, sem modificar `.env` ou exibir a URL/senha.
- Matriz focada em PostgreSQL: **13 passaram, sem skips** em 83,17 s. Inclui `test_tenant_hostname_activation_migration.py`, os dois testes de `test_tenant_hostname_activation_postgres.py`, `test_platform_console_status.py` e quatro contratos de rota/diretório do console.
- A prova DDL real verificou upgrade aditivo, downgrade com auditoria antiga preservada, recusa do downgrade com evento novo (inclusive recusa sem hash), validação de hash/contexto e preservação dos triggers contra UPDATE, DELETE e TRUNCATE.
- As duas corridas reais verificaram um único evento para replay concorrente e consumo único de um passo TOTP ao tentar liberar dois tenants. O segundo caso carrega o proprietário antes da disputa para detectar estado antigo no identity map.
- Complemento após revisão: **3 passaram** em 24,38 s — intenção com hash divergente, redaction de senha/TOTP em erro 422 e cadeia linear real `0090→0107` preservando proprietário, envelope TOTP e carteira. O teste linear mantém o checkpoint anterior `0106` e verifica a extensão `0107`.
- `frontend/app/admin/platform/page.test.tsx`: **7 passaram**. Cobrem host reservado/pronto, bloqueio sem hash, atestação explícita e limpeza de hash/atestação/credenciais ao consultar outro fotógrafo.
- Ruff dos módulos/testes/migration afetados: passou. ESLint dos dois arquivos da página: passou, sem warnings.
- `npx tsc --noEmit --pretty false`: exit 0. O build final, posterior à limpeza de formulário, repetiu a checagem TypeScript e terminou com exit 0 (`npm run build`, Next.js 16.4.2).
- `python -m alembic heads`: `20261107_0107 (head)`.
- `openspec validate enable-tenant-subdomain-ingress --strict`: válido.

## Revisão proporcional de código

- Foram reutilizados autorização PlatformOwner, reautenticação, passo TOTP único, rota sensível, UUID de intenção e auditoria existentes; não foi criada uma segunda política de autorização ou resolução de tenant.
- A revisão acrescentou refresh do proprietário sob lock para impedir TOTP antigo no identity map, rejeição explícita de status nulo no CHECK de evento de sucesso e limpeza da atestação ao trocar de conta. O teste estrutural que apenas espelhava chamadas da migration foi retirado após a prova DDL real.
- Não houve limpeza/reformatação ampla nem descarte de alterações preexistentes. O resolvedor de host já atendia ao contrato; somente a cobertura foi ampliada.

## Achado da execução ampliada

A execução PostgreSQL ampliada de console/status/corridas parou com **14 passed, 1 failed**. A falha foi `test_drive_source_exposes_only_persisted_owner_state_and_quota_without_claiming_health`: `reauthorization_required` tem 24 caracteres e não cabe no `VARCHAR(16)` de `GoogleDriveConnection.state` e da migration `0098`. Essa definição é anterior à change de ingresso e não foi alterada aqui. O bloqueio do release e a necessidade de correção aditiva foram registrados em `../add-google-drive-storage-foundation/release-readiness.md`. Não se afirma que a suíte completa do SaaS está verde.

Continuação autorizada em 07/11: o defeito foi corrigido na própria change Drive, com ORM de 32 caracteres e migration aditiva 0108. O teste antes falho, migration, cadeia 0090→0108 e OAuth passaram em uma matriz de 35 testes. O head local atual é 0108; o checkpoint 0107 acima continua sendo a evidência da implementação do ingresso. Nenhuma migration remota foi executada.

## Inventário externo e limites

- A consulta autenticada Cloudflare confirmou exatamente os dois A existentes em DNS-only e DNSSEC ativo. O inventário SSH somente leitura confirmou NPM 2.15.1/digest, rotas, redes, arquivos de credenciais/configuração e os probes raiz 404 e `markina` 200 com TLS válido; ver `operations-inventory.md`.
- O NPM armazenaria a credencial DNS em JSON no SQLite 0644, com diretórios ascendentes atravessáveis; o arquivo 0600 que ele gera para Certbot não elimina essa cópia. O plugin Cloudflare não está instalado. Custódia, recuperação e ensaio de emissão/renovação são gates reais pendentes.
- Nenhum registro DNS, certificado, rota NPM, serviço ou schema de produção foi alterado. Não houve criação de token, instalação de plugin, reload/restart nem promoção de hostname real a `ready`.
- Não foi feita migration/reinicialização da demonstração de UI em `15472`; as provas locais usaram schemas sintéticos exclusivos em `15470`, removidos pelas fixtures ao terminar.
- Neste checkpoint de 07/11, as tasks 3.2, 3.3, 3.4, 4.1, 4.2 e 4.4 continuavam abertas. A task 3.2 foi posteriormente concluída conforme o registro de 08/11 abaixo; as demais seguem vinculadas à custódia, release compatível e autorizações específicas. A change não está pronta para sincronização/arquivo ou publicação.

## Publicação autorizada do DNS wildcard — 08/11/2026

- Autorização expressa do proprietário: “Sim, autorizo esse registro”, para criar somente A `*.pickyourpic.com.br` → `132.145.193.169`, proxy desligado. A operação foi realizada pela aba autenticada Cloudflare compartilhada, sem usar token ou alterar credenciais.
- Antes da escrita: tabela completa com dois A exatos, raiz e `markina`, IP `132.145.193.169`, DNS-only, TTL 1 hora. Consulta pública confirmou NS `kara.ns.cloudflare.com`/`mustafa.ns.cloudflare.com` e DS `2371 13 2`, coerentes com o inventário.
- Depois de salvar: tabela com três A. Novo wildcard no IP aprovado, DNS-only e TTL Auto; os dois registros exatos preservaram IP, proxy e TTL. Captura visual do painel foi exibida durante a execução.
- Consulta pública DNS-over-HTTPS ao resolvedor Cloudflare (`Accept: application/dns-json`, `type=A&do=true`): raiz, `markina` e `saas-readiness-probe-20261108.pickyourpic.com.br` retornaram `Status=0`, `AD=true` e A `132.145.193.169`. TTL observado: 3600 s nos nomes exatos, 300 s no sintético. Isso comprova a resposta assinada observada nesse resolvedor, não todos os caches da Internet.
- Probes HTTPS HEAD com validação TLS: raiz HTTP 404 e `markina` HTTP 200, ambos `ssl_verify_result=0`, coerentes com a referência anterior.
- Escopo realizado: somente criação do A wildcard. Sem certificado, token DNS-01, rota NPM, reload/restart, migration, deploy ou promoção de hostname a `ready`. Não houve alteração no Registro.br. DNS wildcard não demonstra TLS nem isolamento no runtime.
- Recuperação delimitada, se futuramente necessária e autorizada: remover exclusivamente o novo A wildcard, preservando os registros exatos; caches podem manter resposta até o TTL. Nenhuma remoção foi executada.
- Task 3.2 concluída. Tasks 3.3/3.4 e validação integrada continuam bloqueadas pelos respectivos gates de custódia, runtime e autorização. Revisão proporcional: mudança operacional e documental, sem código funcional afetado ou refatoração elegível.
- Validação documental posterior: `openspec validate enable-tenant-subdomain-ingress --strict` e `openspec validate add-photographer-signup-portal --strict` passaram. `git diff --check` dos dois diretórios não reportou erro nos arquivos rastreados; como há artefatos ainda não rastreados, esse comando não cobre toda a documentação. Os trechos editados e as tasks pendentes foram relidos; nenhum código de runtime foi modificado nesta operação.

### Migrations de reserva e ativação em PostgreSQL — 15/11/2026

Reserva de hostname e auditoria de ativação passaram nos dois testes de migrations reais do lote `C:/codex-data/local-review/prepush-remaining-postgres-20261115.xml`: expansão aditiva, preservação do legado e recusa de downgrade que perderia evidência nova. O comando tem 11 aprovações, 1 falha histórica de fixture e 1 skip em outros casos, documentados e resolvidos separadamente. Banco sintético 15470, schemas descartáveis; sem DNS, TLS, proxy ou promoção de hostname real.

## Revisão semântica cruzada do ingresso SaaS — 15/11/2026

A comparação com `add-photographer-signup-portal` não encontrou conflito: verificar e-mail e definir senha ativa a conta exploratória, mas a reserva do hostname continua em `reserved`; links/rotas só ficam disponíveis após gates de infraestrutura, runtime e isolamento e promoção explícita, owner-only e auditada. A ativação da conta não publica nem autoriza o hostname.

O A wildcard foi a única escrita externa desta change, autorizada e executada em 08/11; os registros explícitos de raiz e `markina` foram preservados. O DNS público com DNSSEC retorna o IP da origem para um hostname sintético, mas a evidência HTTPS mais recente em `../add-photographer-signup-portal/production-release-readiness.md` (12/11) registra falha no handshake TLS desse hostname, sem determinar se a causa é certificado, NPM ou política TLS. Portanto DNS não demonstra TLS, rota ou tenant isolado.

O inventário operacional datado de 07/11 identifica que o SQLite do NPM exporia a credencial caso ela fosse armazenada ali; nenhuma credencial DNS estava configurada. Não guardar ali o token. O emissor/helper foi preparado e testado localmente, sem instalação no Oracle, emissão pública ou ensaio de renovação. Permanecem pendentes 3.3, 3.4, 4.1, 4.2 e 4.4. Não houve certificado, token real, rota NPM, promoção de host ou alteração de produção nesta revisão.

OpenSpec strict passou e o scan de whitespace está limpo. Os testes de migrations de 15/11 foram lidos do relatório existente (13 casos, 11 aprovados, 1 falha histórica de fixture e 1 skip); os dois casos de reserva/auditoria passaram. Nenhum teste de aplicação foi repetido.
