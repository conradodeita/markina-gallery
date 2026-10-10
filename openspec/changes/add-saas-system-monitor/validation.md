# Evidências de implementação — 09/10/2026

## Jornada autenticada do proprietário e correção da disputa de consultas

Após login normal realizado pelo proprietário no navegador remoto autorizado, `/admin/system-monitor` exibiu a conta esperada, estado Saudável, CPU/RAM/disco/rede/I/O, séries, percentis com lacunas e versão 777495b. A árvore consultada retornou cinco fotógrafos e 16 clientes; expansão de ramo, filtro Ativo agora, busca sem correspondência e restauração da consulta funcionaram. Sinal real passou a indicar uma conta ativa, sem equiparar as outras sessões válidas a atividade. Card preservado foi consultado e mostrou pool/PostgreSQL/cinco filas, mantendo orçamento global indisponível por inventário incompleto. Não foram criadas sessões, contas ou dados de domínio pelo executor.

Exportações efetivamente baixadas pelos botões autenticados: JSON **104.787 bytes** e texto **104.854 bytes**; JSON válido, staging/777495b/healthy, **59 snapshots**, três tipos de operação. Verificações dos dois arquivos não encontraram e-mail, UUID de negócio ou chaves cookie/token/password/otp/phone/email. Arquivos ficam fora do Git; nomes/identidades da árvore não são registrados nesta evidência. Paginação não foi exercitada no navegador porque nenhuma página excedeu 25 itens; contrato de paginação permanece coberto por Vitest e SQL.

Na carga inicial da página, árvore recebeu **429**, enquanto resumo e incidentes responderam 200. Atualização explícita da árvore respondeu 200. A fronteira foi delimitada: três pedidos iniciais competiam pelo `BoundedSemaphore(2)` das rotas do monitor. Regressão Vitest com o contrato de duas consultas falhou antes da correção (incidentes indisponíveis) e passou após fila serial compartilhada somente entre pedidos do monitor nesse contexto do navegador. Não houve expansão do limite do backend nem retry automático. Testes verificam ordem/opções privadas, cancelamento de pedido na fila sem rede, progresso após falha e ausência de repetição. **12 testes focados aprovados**, 2,74 s. Correção ainda exige publicação e repetição da abertura inicial no servidor; não considerar a jornada corrigida validada remotamente neste SHA.

Checkpoint após correção: `npm test -- --maxWorkers=2` **467 passed**, 59 arquivos, 129,70 s; `npm run lint` aprovado com 0 erros e 37 avisos preexistentes fora dos arquivos do monitor; `npm run build` aprovado com TypeScript e 23 páginas, incluindo monitor. Somente Vitest/jsdom e build estático, sem servidor local. Evidência visual do painel autenticado observada no navegador remoto; captura privada fora do Git, sem clientes expandidos. Specs continuam sem sincronização/arquivo até revisão humana. Task 6.2 permanece aberta para validar a nova publicação.

## Publicação, ativação e validação real no servidor

PR #151 publicado por workflow `38000212755` SUCCESS, SHA remoto `777495b012bb98174e50c07b15dd507b329b8de4`, schema 0072, Git limpo. Propriedade e quatro grants reais aplicados à conta indicada pelo proprietário, auditados. Coleta ativa nos seis processos, timer de snapshot privado 60 s instalado e API com bind somente leitura. Detalhes, falhas operacionais delimitadas/corrigidas e fingerprint de terceiros em `deployment-inventory-20261009.md`.

No container API do servidor autorizado: oito tabelas confirmadas, permissões do proprietário revalidadas pelo gate, relatório real gerado e exportado em memória (**106.367 bytes**, intervalo 60 min, **60 snapshots**, três tipos de operação, idade **96,99 s** no instante verificado, estado calculado **healthy**). Host observado com CPU, RAM, disco, rede e I/O; versão reportada corresponde a 777495b. Exportação sem e-mail do proprietário ou UUIDs de negócio; conteúdo privado não foi persistido no repositório. Lock PostgreSQL com chave isolada 73419073 verificou exclusão em segunda conexão e liberação após rollback; não disputou o lock de coleta 73419072.

Quatro GETs anônimos contra a origem pública autorizada (summary/tree/incidents/report) retornaram **403** com `no-store`. Navegador real abriu `/admin/system-monitor` e, sem sessão, redirecionou ao login de fotógrafo com return_to correto. Depois, o proprietário realizou login normal e a jornada positiva foi exercitada conforme seção acima; nenhuma senha/TOTP/cookie extraída ou sessão fabricada.

Correção operacional reutilizável: CLI de host agora compatível com Python 3.8, alvo Ruff específico nesse arquivo e wrapper de deploy retém overlay privado autorizado quando o arquivo do repositório também existe, fornecendo versão do checkout atual inclusive rollback. **29 testes do monitor aprovados (4,25 s)**, Ruff completo aprovado, AST Python 3.8 aprovado, `scripts/test_deploy_homolog.sh` completo aprovado sob Git Bash (políticas de deploy/manutenção/facial e novo contrato do overlay/versão), shell syntax aprovada. Coletor efetivamente executado no Python 3.8 do Oracle e hash conferido. Sem nova carga ou campanha funcional A+B. Publicar o ajuste por PR e pausar enquanto CI executa, conforme instrução humana.

## Correção da integração na terceira execução do CI

Execução `37993782959`, commit `d925a94a5db84be60179bf3006b829f3dba25fa7`: frontend, OpenSpec, gitleaks, Ruff e verificações operacionais aprovados. Pytest executou a suíte completa e registrou **1.277 passed, 11 failed, 20 skipped**, 1.422,21 s. As onze falhas foram delimitadas em três causas:

- Fixture de diagnóstico facial não indicava proprietário, retornando 403 conforme o novo contrato. Agora indica proprietário sintético explicitamente; os testes existentes de negação a não proprietário permanecem.
- Inventário fechado de limpeza não classificava as oito tabelas novas. A política agora preserva essas tabelas e auditoria `system_monitor.*`, com registro dos modelos também no CLI independente. Nada foi acrescentado à lista de exclusão operacional. FK de atividade acompanha exclusão de sessão de cliente, conforme spec.
- Conferência do catálogo histórico 0070 tentava ler tabelas posteriores; agora exige que elas estejam ausentes e verifica o restante do catálogo. Testes da rotina atual de inventário/limpeza migram até 0072; caso PostgreSQL de preservação verifica proprietário, grants, bucket, sinal administrativo e auditoria.

Validação permitida da correção: `DATABASE_URL=sqlite:// python -m pytest tests/test_system_monitor.py tests/test_homolog_cleanup.py tests/test_capacity_observability_contracts.py -q --tb=short` na pasta backend: **43 passed, 1 skipped, 7,12 s**. Ruff completo aprovado após ajustar import; compilação Python dos arquivos afetados aprovada. `pytest tests/test_tenant_photographer_migration.py tests/test_tenant_migration.py -q -rs --tb=short`: **4 passed, 18 skipped, 32,73 s**, com casos PostgreSQL não executados localmente. OpenSpec estrito aprovado. Endpoint com TestClient e migrations PostgreSQL serão verificados no novo CI; nenhum servidor/container local ou limpeza real iniciado/executado. Pausa solicitada permanece após push, sem merge/deploy.

## Estado e escopo

### Continuação autorizada e envio ao CI — 09/10/2026

O proprietário autorizou a etapa 6.2 e pediu pausa enquanto o CI executa, retornando pessoalmente com o resultado. Autorização operacional concedida; nenhuma migration/deploy/configuração/grant real executada nesta preparação. Antes da operação remota, atualizar inventário, portas/subdomínio e plano de impacto conforme AGENTS.md.

Entrega para revisão preparada na worktree `C:\codex-data\worktrees\saas-system-monitor\Photo Delivery`, branch `feature/saas-system-monitor`, sobre `develop` em `d4d000de3b41d4b2c7c96197cfea28b7940c5aea`. Transferidos somente os arquivos/diffs do monitor; os 42 commits da campanha fora de develop e as alterações locais não relacionadas permanecem na worktree original. A integração do layout preserva `AdminSessionToolbar` do develop atual.

Nesta nova base, Ruff completo de `backend/app backend/tests` passou sem exceções, OpenSpec estrito passou e `git diff --check` passou. Os resultados de testes/build abaixo documentam a base anterior; o CI do PR verificará a integração com o develop atual. Não considerar esse CI aprovado até receber seu resultado. Não fazer merge automático, polling contínuo nem deploy durante a pausa solicitada.

### Diagnóstico do CI do PR #151 — 09/10/2026

Execução `37992103930`, commit `035197c5b29be4c913f8541f632919bd629e3631`: OpenSpec e gitleaks passaram; frontend teve 462 testes aprovados e uma falha em `app/pwa-contract.test.ts:46`. O teste exigia literalmente `SessionBoundary` contendo apenas children; a instrumentação adicionou `MonitorActivity` dentro dessa mesma fronteira. Ajustado o contrato para exigir um único componente de atividade, mantendo botão de instalação único, toolbar global, shells sem duplicação e contraste. Nenhum código de produto foi alterado para contornar o teste.

Backend falhou antes do checkout/testes, ao baixar `postgres:17-alpine`: Docker Hub respondeu `toomanyrequests` nas três tentativas do runner. Os dois serviços sintéticos do CI passaram a usar `public.ecr.aws/docker/library/postgres:17-alpine`, espelho de Docker Official Images. Consulta somente leitura do manifesto retornou HTTP 200 e confirmou Linux amd64; não baixou/executou containers locais. YAML validado, OpenSpec estrito e diff check aprovados. Execução efetiva dos serviços continua dependente do novo CI. Imagens/configuração do servidor publicado não foram alteradas.

### Evidências anteriores à preparação do PR

Correção do segundo CI validada por `pytest tests/test_capacity_observability_contracts.py -q --tb=short` (**4 passed, 0,09 s**), `ruff check app tests` (**aprovado**) e `ruff check tests/test_capacity_observability_contracts.py --select RUF100` (**aprovado**), na pasta backend. O cenário de rejeição do timestamp sem fuso permanece coberto. Aguardar próximo CI antes do merge.

### Segunda execução do CI — 09/10/2026

Execução `37993351340`, commit `c2edca95f68ad69542bb321ff9b8098219e65f30`: frontend completo (lint/testes/build), OpenSpec e gitleaks aprovados; serviços PostgreSQL inicializados com sucesso pelo espelho. Backend interrompido no Ruff por `RUF100` em `test_capacity_observability_contracts.py:51`: exceção `noqa: DTZ001` para regra não habilitada na configuração usada pelo CI. A configuração local habilita DTZ001; para manter o contrato nas duas configurações, o teste deriva o timestamp ingênuo de `NOW.replace(tzinfo=None)` sem exceção de lint. Preservados comentário e expectativa de rejeição. Sem mudança no comportamento do produto.

Validação da correção na worktree do PR: `npm ci --no-audit --no-fund`, `npm test -- --maxWorkers=2` (**463 passed, 58 arquivos, 140,86 s**), `npm run lint` (**0 erros; 37 avisos em arquivos fora desta correção**) e `npm run build` (**aprovado**, TypeScript e 23 páginas, incluindo monitor). Nenhum servidor de aplicação iniciado. Novo CI após push deverá confirmar os serviços PostgreSQL no runner; manter a pausa solicitada até retorno do usuário.

Código implementado na worktree `C:\codex-data\worktrees\invite-only-otp\Photo Delivery`, branch `codex/remote-test-campaign`, base `8d02583da8252de6f5b877128520d29d0e2428e4`, com alterações ainda sem commit naquele momento. Nenhum deploy, migration real, concessão real, edição de `.env`/segredos, início de aplicação/containers local ou campanha de carga foi executado. Testes aqui são funções/ORM com SQLite sintético descartável, Vitest/jsdom e compilação estática. A leitura SSH foi exclusivamente de inventário/fontes do servidor autorizado, sem tocar em dados ou resultados A+B.

## Entregas efetivas

- Página `/admin/system-monitor` com resumo, gráficos e tabelas acessíveis, qualidade/idade dos dados, filas, processamento, host, armazenamento, árvore sob demanda, incidentes e exportação JSON/texto. Card antigo preservado com seu contrato.
- Propriedade única persistida por UUID em `platform_owner`, além dos grants separados. Troca/verificação de e-mail mantém propriedade; outra conta com e-mail anterior não herda acesso. Novo monitor e diagnósticos antigos de capacidade/facial exigem propriedade no backend. O endereço atual só identifica a conta na futura indicação inicial; não há e-mail fixo na regra de autorização.
- Instrumentação opt-in HTTP, aquisição de pool e ciclos de workers; buffers limitados, UPSERTs agregados, snapshots, histogramas, fontes isoladas, retenção e alertas deduplicados.
- Árvore paginada por tenant, pesquisa/filtro em SQL, atividade visível autenticada limitada, sessão distinta de presença; nomes fora das exportações.
- Adaptador de host com schema fechado e coletor Linux stdlib opcional, sem instalação. Inventário limitado de metadados dos arquivos cadastrados; total nulo quando incompleto.
- Migration aditiva de oito tabelas, vazia de permissões/proprietário, compilada offline para PostgreSQL. CLI de propriedade inicial/grants com dry-run, confirmação por UUID/e-mail atual e recusa de transferência implícita.
- Documentação operacional e overlay Compose inativo, sem portas/volumes adicionais.

## Resultados reais

| Validação | Resultado |
|---|---|
| Backend integrado: monitor, proprietário/operador, contratos/coletores/pool/filas/banco, runtime facial e ownership | **93 passed, 1 skipped**, 121,04 s na repetição final; inclui os 28 testes do monitor |
| Teste pulado | `test_tenant_ownership_schema.py:91`: conferência do catálogo exige PostgreSQL; não substituída por SQLite |
| Frontend monitor + capacidade + navigation + session-boundary + admin page | **62 passed**, 7 arquivos, 12,93 s na repetição final; inclui máximo zero real no gráfico e atualidade calculada a partir da idade fornecida pelo servidor |
| Build Next.js 16.3.2 | **Passou**; compilação, TypeScript e geração de 23 páginas, incluindo `/admin/system-monitor`; nenhum `next start`/servidor iniciado |
| TypeScript independente | `tsc --noEmit`: **passou** |
| ESLint dos arquivos tocados de frontend | **passou** |
| Ruff de novos módulos/testes e integrações tocadas | **passou**, com as duas exceções preexistentes delimitadas abaixo |
| OpenSpec | `validate add-saas-system-monitor --strict`: **válida** |
| Overlay Compose | YAML parseado; seis serviços existentes; ausência de novas portas/volumes verificada estaticamente; Compose não iniciado |
| Diff | `git diff --check`: sem erro de whitespace; avisos Git de normalização LF/CRLF somente |

Ruff preserva duas condições anteriores ao trabalho: ordem de imports em `app/main.py` (`I001`, especificamente bloco remoto OTP) e `from __future__ import with_statement` em `migrations/env.py` (`UP010`). Esses dois arquivos foram checados ignorando somente a regra preexistente correspondente; todos os demais códigos de lint seguem ativos. Não foi feita limpeza/reformatação da campanha para remover esses avisos. Pytest também emitiu warnings de depreciação de `FastAPI.on_event`; não são falhas de execução.

Revisão final com Jev e inspeção direta de código conferiu autorização por UUID, projeção fechada e limites. Foi acrescentado teste de regressão para revogação da permissão `incidents` durante uma exportação: o relatório inteiro é recusado antes da entrega se contiver incidentes cuja concessão foi revogada. A contagem de timeouts de aquisição de conexão foi separada das demais falhas do pool, com persistência, projeção e card próprios; o teste distingue timeout de outra exceção. Backend, frontend, lint e build foram repetidos e aprovados após esses ajustes e os de idade dos dados/gráfico; sem processo Node de servidor iniciado.

## Falha adicional delimitada, sem resultado positivo presumido

Execução extra de `test_tenant_media_jobs.py` e quatro testes unitários de ajuste de prévia: **8 passed, 1 failed**. Falha: `test_suspensao_durante_render_nao_publica_A_e_worker_avanca_B`, `sqlite3.OperationalError: database is locked` ao tentar suspender um tenant por segunda conexão durante renderização com transação de escrita já aberta. O erro ocorre em `media.generate_derivatives → Image.save → suspend → commit`, antes do worker avançar para a outra conta.

Hipótese delimitada: fixture SQLite de arquivo/NullPool não reproduz a concorrência PostgreSQL requerida pelo teste. Repetição com `SYSTEM_MONITOR_ENABLED=false` e decorators removidos em memória (`.__wrapped__` de worker e ajuste) falhou no mesmo ponto. A falha independe da instrumentação adicionada; nenhum código de mídia nem a fixture A+B foram modificados para forçar aprovação. A validação desse cenário segue pendente no PostgreSQL remoto autorizado. Essa execução não é apresentada como suíte integral aprovada.

## Inspeção remota somente leitura

No servidor autorizado, SSH em modo BatchMode/StrictHostKeyChecking confirmou procfs legível para CPU, RAM, rede e disco. `systemctl is-active oracle-cloud-agent` retornou `inactive`; CLI OCI ausente. Foram listados apenas nomes dos treze containers com label do projeto `markina-gallery`. Não foi confirmado acesso IAM/Monitoring/quota, nem coletadas métricas de teste da aplicação. Não houve instalação ou mudança de infraestrutura.

## Comandos reproduzíveis executados

Na pasta `backend`, com `DATABASE_URL=sqlite://` no processo de teste (nenhum arquivo de configuração editado):

```powershell
$env:DATABASE_URL='sqlite://'
python -m pytest tests/test_system_monitor.py tests/test_tenant_installation_operator.py tests/test_capacity_observability_contracts.py tests/test_capacity_observability_collector.py tests/test_capacity_observability_pool.py tests/test_capacity_observability_queues.py tests/test_capacity_observability_budget.py tests/test_capacity_observability_database.py tests/test_facial_runtime.py tests/test_tenant_ownership_schema.py -q -rs --tb=short
python -m ruff check app/system_monitor tests/test_system_monitor.py tests/test_tenant_installation_operator.py app/auth.py app/worker.py app/facial/runtime.py app/preview_adjustment/service.py app/preview_adjustment/worker.py migrations/versions/20261009_0072_system_monitor.py
python -m ruff check app/main.py --ignore I001
python -m ruff check migrations/env.py --ignore UP010
```

Na pasta `frontend`:

```powershell
node node_modules/vitest/vitest.mjs run app/admin/system-monitor/monitor.test.tsx app/admin/capacity-report.test.ts app/admin/capacity-diagnostics.test.tsx app/admin/installation-diagnostics.test.tsx app/admin/admin-navigation.test.tsx app/session-boundary.test.tsx app/admin/page.test.tsx --maxWorkers=2
node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js app/admin/system-monitor app/monitor-activity.tsx app/admin/admin-navigation.tsx app/layout.tsx
node node_modules/next/dist/bin/next build
```

Na raiz: `openspec validate add-saas-system-monitor --strict` (nesta máquina executado com Node e CLI existente no cache npm, sem instalação de dependência) e `git diff --check`.

## Arquivos desta change

Criados:

- `backend/app/system_monitor/`: `__init__.py`, `access.py`, `activity.py`, `config.py`, `grants.py`, `host.py`, `host_collect.py`, `incidents.py`, `models.py`, `pool.py`, `report.py`, `routes.py`, `runtime.py`, `sanitize.py`, `sources.py`, `storage.py`, `store.py`, `telemetry.py`.
- `backend/migrations/versions/20261009_0072_system_monitor.py`, `backend/tests/test_system_monitor.py`.
- `frontend/app/admin/system-monitor/`: `page.tsx`, `types.ts`, `user-tree.tsx`, `use-permissions.ts`, `monitor-link.tsx`, `monitor.module.css`, `monitor.test.tsx`.
- `frontend/app/monitor-activity.tsx`, `docker/docker-compose.system-monitor.yml`, `docs/system-monitor.md`.
- `openspec/changes/add-saas-system-monitor/`: proposal, design, tasks, validation e deltas de `auth/administrative-activity`, `deployment-operations/system-monitor` e `deployment-operations/admin-capacity-diagnostics`.

Alterados neste escopo:

- `backend/app/auth.py`, `main.py`, `ownership_schema.py`, `worker.py`, `facial/runtime.py`, `preview_adjustment/service.py`, `preview_adjustment/worker.py`: integração e autorização.
- `backend/migrations/env.py`: registro de metadata dos novos modelos.
- `backend/tests/test_tenant_installation_operator.py`: fixture agora indica explicitamente proprietário sintético para o contrato restrito.
- `frontend/app/admin/admin-navigation.tsx`, `frontend/app/layout.tsx`: navegação e sinal de atividade.
- `docs/admin-capacity-diagnostics.md`: vínculo com o novo monitor e gate operacional.

Alterações preexistentes em `backend/tests/pilot_fixture.py` e documentos das changes de piloto, OTP, seleção finalizada e capa foram preservadas; não pertencem a este escopo. Sem commit/push, sincronização ou arquivamento nesta execução.

## Pendências reais e acesso

1. Aprovação operacional para migration, publicação da versão revisada, indicação inicial do UUID proprietário e grants, e ativação explícita da coleta. Não há grant/configuração real aplicada nesta execução.
2. Fonte do host: scheduler de 60 s, diretório privado com UID/grupo compatíveis e montagem somente leitura na API. OCI Monitoring/IAM/quota não disponíveis/confirmados; sem cliente OCI ou contratação implementados.
3. Validação remota PostgreSQL (incluindo advisory lock/concorrência, migration e catálogo) e jornadas Playwright autenticadas após publicação. Sem carga; contas sintéticas independentes; manter campanha A+B intacta. O harness remoto existente não foi executado contra código ainda não publicado.
4. Revisão humana antes de sincronizar specs/arquivar. O restante independente está implementado e validado dentro desses limites; não declarar a task 6.2 concluída.

Após publicação, abrir **Administração → Monitor do sistema**, caminho `/admin/system-monitor`, pela conta proprietária com grants. No servidor atual esse novo painel ainda não foi disponibilizado por esta tarefa. Retenção, percentis aproximados, cobertura parcial do inventário de arquivos, perdas de buffers, escopo de pool por processo e ausência de prova de capacidade máxima estão descritos em `docs/system-monitor.md` e no próprio relatório exportável.
