# Investigação e validação — 25/09/2026

## Escopo e estado inicial

Pedido: investigar antes de alterar, recolher cards de Notificações, auditar conservadoramente, validar e não executar commit/push. Mandato, roadmap, diretrizes, config OpenSpec, spec de operação e changes de notificações/entrega foram consultados. A central não possui spec principal consolidada; seus contratos permanecem nas changes ativas. OpenSpec disponível via `npx -y @fission-ai/openspec@latest`.

O status inicial já continha `backend/app/facial/purge.py`, `.codex-tmp/` e documentos de outras changes. Nenhum deles foi editado por esta execução. Bancos locais, inclusive arquivos com nomes de testes e journals, foram preservados.

## Cards

- Não existe accordion compartilhado; `details/summary` já é usado em Pagamentos. Reutilizado o padrão nativo, sem dependência ou estado persistido.
- Sete cards inicialmente fechados, independentes; cabeçalho contém destinatário, título e seta. Formulários continuam montados e mantêm rascunhos, mensagens e campos. GET inicial e PUT de salvamento não foram alterados.
- Cinco testes focados passaram: conteúdo existente, abertura independente sem API, rascunhos, salvamento, erro e recuperação da carga.
- QA Edge headless com API interceptada e dados sintéticos passou nas seis combinações 390/768/1440 × claro/escuro. Verificou Enter/Espaço, clique, rascunho, canais, zero chamadas ao alternar, salvamento explícito, todos os campos expandidos e ausência de overflow. Capturas inspecionadas; resultados locais em `%TEMP%/pick-your-pic-notification-cards-qa/results.json`.
- Script QA atualizado de seis para sete eventos e adaptado ao diálogo existente de escolha de push. Falhas iniciais do roteiro eram seleção do label com contador, foco preso no diálogo e índices de locator mutável; corrigidas no roteiro, sem alterar a aplicação para satisfazer testes.

## Relato adicional de entrega

O proprietário relatou ausência de push/WhatsApp e nenhuma mensagem visível após Enviar.

- Causa de push comprovada: produtor usa `/library/purchases#order-UUID`, mas `web_push.safe_target` e `allowedPushPath` não aceitavam esse destino. Testes adicionados falharam antes da correção (`invalid_destination` no backend e zero chamadas a showNotification no service worker).
- Correção limitada à allowlist da rota de compras com fragmento opcional de UUID canônico nos dois pontos. Queries, URLs externas e fragmentos arbitrários continuam rejeitados. Sem alteração de gates, chaves, destinatários, filas, dados ou reenvio retroativo.
- Após correção: 22 testes do adaptador real com HTTP falso passaram; 11 testes frontend de service worker e cards passaram. Inclui cifragem VAPID, recebimento, abertura/foco da aba e destinos rejeitados.
- Consulta pública somente leitura à homologação documentada no repositório: `/api/health` e `/markina-sw.js` retornaram HTTP 200; o service worker publicado ainda contém a allowlist antiga. Nenhuma sessão, API privada ou registro de usuário foi consultado. Isso confirma a incompatibilidade no artefato publicado, sem presumir o estado das filas/credenciais reais.
- Retorno visual: teste integrado da página de Pagamentos confirma que “Fotos disponíveis em Compras. Aviso agendado.” permanece após atualizar a lista, com card aberto e Reenviar aviso habilitado. Treze testes de página/formulário passaram. O sumiço relatado não foi reproduzido localmente; não houve alteração especulativa do formulário.
- Os bundles públicos da página de Pagamentos da homologação também contêm os textos de sucesso, ausência de canais e Reenviar aviso. Isso não comprova a execução do fluxo no dispositivo do proprietário, mas afasta a ausência desses textos no artefato servido. Consulta somente a HTML/JavaScript públicos.
- WhatsApp: caminho rastreado de set_delivery/enqueue_event até process_next_notification, gates, canal e telefone verificado. Não é afetado pela allowlist de push. Causa no ambiente real ainda não comprovada; solicitado endereço do site e se OTP/pagamentos continuam chegando. Nenhuma mensagem real foi enviada e nenhum banco real foi consultado.
- Validação focada adicional: `test_order_delivery.py`, `test_notification_delivery.py`, `test_notification_settings.py`: 32 passaram em 6,70 s com banco descartável exclusivo e provedores simulados. Inclui envio WhatsApp aceito, canais independentes, falhas, deduplicação, revisão financeira e autorização. Não comprova transporte real nem justifica habilitar gates automaticamente.

## Auditoria e decisões conservadoras

- Buscas no código de aplicação não localizaram console.log/debug, debugger, breakpoint ou pdb.set_trace. Prints do worker são diagnóstico operacional e foram mantidos.
- Ruff completo passou. ESLint passou sem erros, com 28 avisos existentes (imagens, navegação, ref do carrinho e assinaturas de mocks).
- Inspeção adicional de TypeScript com noUnusedLocals/noUnusedParameters apontou somente parâmetros de mocks. Suas assinaturas são usadas para tipar mock.calls e as asserções de requisições; não foram removidas automaticamente.
- Não se comprovou componente/arquivo de produção morto removível com segurança. Rotas Next.js, workers, migrations, scripts operacionais e referências históricas foram mantidos.
- Quatro caches conhecidos inventariados: `.pytest_cache`, `.ruff_cache`, `backend/.pytest_cache`, `backend/.ruff_cache`. A revisão automática bloqueou o comando de limpeza com “blocked by policy”, sem justificativa detalhada. Nenhum cache foi apagado; não se tentou contornar o bloqueio com outra ferramenta.
- Inventário de caches: respectivamente 5 arquivos/1.358 bytes, 5/2.227, 6/95.126 e 32/33.137 (total 48 arquivos/131.848 bytes). São pequenos; mantê-los não altera a aplicação.
- `.codex-tmp`, bancos/journals, referências faciais, modelos, uploads, mídia, dependências e build foram preservados por origem/conteúdo ou utilidade incertos.

## Validação de integração

- Frontend final: 47 arquivos, 348 testes passaram após a extensão de push e teste integrado do retorno de entrega.
- Build Next.js final passou, incluindo TypeScript. Houve falha intermediária em uma opção `exact` acrescentada ao teste integrado (não suportada por Testing Library); corrigida removendo a opção redundante. Nenhum código de produto foi alterado para contornar validação.
- Testes operacionais: preservação de branding 12 passaram e 2 ignorados (fixture Docker explícita e privilégio de symlink); políticas de deploy e manutenção passaram. Não executam deploy nem manutenção real.
- `scripts/test_deploy_homolog.sh` passou via Git Bash, incluindo políticas de deploy, manutenção, produção facial e rollout. Gitleaks 8.24.3 sobre o diff desta execução e os novos artefatos OpenSpec: nenhum segredo encontrado.
- OpenSpec estrito global inicial: 61 itens válidos. Informativos preexistentes sobre compatibilidade de archive não foram alterados; nenhuma spec foi sincronizada ou arquivada.
- Docker Compose config com `--quiet --no-env-resolution --no-interpolate` passou. Build web tentado e bloqueado: daemon `dockerDesktopLinuxEngine` indisponível. Não iniciar Docker global, containers, redes ou volumes em máquina compartilhada. Nenhum deploy executado.
- Backend: execução sempre com SQLite novo em `%TEMP%`, mídias/branding/referências isolados, transportes sandbox e sem PostgreSQL operacional. Primeira tentativa com APP_ENV=test foi interrompida por configuração de chave exigida; corrigido somente o ambiente efêmero para development. Suíte completa reiniciada por lentidão de DDL SQLite em Windows: runner temporário aplica synchronous=OFF exclusivamente a conexões SQLite cujo arquivo está sob o diretório descartável da execução, e journal_mode=MEMORY somente ao banco principal tests.sqlite. Bancos específicos de migrations/concorrência preservam seu modo de journal, inclusive WAL explícito. Não representa teste de durabilidade a crash. Runner e log: `%TEMP%/pick-your-pic-maintenance-suite-20g41gwb/`. Resultado final: **821 passaram, 13 ignorados, 106 avisos, 801,94 s**. Nenhuma falha. Avisos existentes de depreciação FastAPI/Starlette/sqlite3; cenários ignorados não representam validação em PostgreSQL real.
- Revisão final do diff: nove arquivos de implementação/testes/QA, com quatro arquivos de produção alterados (página/CSS de Notificações e allowlists de push no backend/service worker). Demais alterações são testes e QA. Nenhuma exclusão de arquivo/código morto realizada. `git diff --check` passou; status mantém as alterações preexistentes fora desta change. Servidor localhost usado no QA encerrado após a validação.

## Arquivos desta execução

- `frontend/app/admin/notifications/page.tsx`
- `frontend/app/admin/notifications/notifications.module.css`
- `frontend/app/admin/notifications/page.test.tsx`
- `frontend/scripts/notification-visual-qa.cjs`
- `frontend/public/markina-sw.js`
- `frontend/app/push-worker.test.ts`
- `frontend/app/admin/payments/page.test.tsx`
- `backend/app/web_push.py`
- `backend/tests/test_web_push.py`
- Artefatos desta change: `.openspec.yaml`, proposal, design, tasks, duas delta specs e este relatório.

Até o encerramento da manutenção local, nenhum commit ou push havia sido feito. A publicação Git foi autorizada posteriormente, conforme registro abaixo. Nenhuma alteração de segredo, migration operacional, deploy ou alteração de dados reais; correção ainda não publicada no site.

## Publicação Git autorizada — 25/09/2026

Após perguntar se faltava push do recolhimento dos cards e receber a confirmação do escopo (cards, correção push e testes), o proprietário solicitou “Vamos terminar isso”. Essa instrução autoriza concluir commit/push e PR, substituindo a restrição inicial somente para publicação Git.

- Branch de publicação: `feature/collapsible-notification-cards`, criada de `origin/develop` em `886334d5cbbc8db64fb592a8e2a28bff50be3dc3`. A árvore dessa base é idêntica à base local anteriormente validada, sem necessidade de reaplicar código.
- Escopo do commit limitado aos nove arquivos listados acima e aos sete artefatos desta change. Documentos de outras changes, `backend/app/facial/purge.py` e `.codex-tmp/` permanecem fora do commit.
- Revisão do diff confirmou somente UI recolhível, allowlists push, testes e QA. As evidências locais de testes/build acima continuam aplicáveis; nenhuma implementação foi alterada nesta retomada.
- CI deverá rodar no PR para `develop`, com acompanhamento de testes, lint, build, OpenSpec e segredos. O resultado remoto e o SHA publicado ficam verificáveis no PR desta branch.
- O workflow faz deploy automático apenas em push para `develop`; publicar a branch e abrir PR não executa deploy. Merge, alterações no servidor e sync/archive permanecem fora desta autorização. Os bloqueios 2.2, 3.2 e 4.1 continuam registrados, sem alegação de limpeza, build Docker ou resolução do WhatsApp.

## Extensão solicitada: servidor de homologação

Após o proprietário solicitar incluir o servidor na higienização, realizado inventário por SSH com chave de host previamente registrada, BatchMode e StrictHostKeyChecking. Somente leituras de metadados, tamanho e saúde; nenhum .env/segredo ou conteúdo de banco/mídia consultado. Consulta limitada ao projeto e inventário geral necessário para preservar terceiros.

- Checkout `/opt/markina-gallery`, limpo em `886334d5cbbc8db64fb592a8e2a28bff50be3dc3`.
- Subdomínio `markina-homolog.duckdns.org`, entrada própria `127.0.0.1:8080`; portas/proxy/DNS/certificados inalterados.
- Disco de 194 GB: 72 GB usados, 122 GB livres, 38% de ocupação.
- Treze containers do projeto em execução, todos saudáveis; API `{"status":"ok","service":"api"}` antes e depois.
- IDs próprios preservados: nginx `ac146213c98d`, web `54327bf603fc`, api `4230954878b9`, worker `d2383efe8d66`, facial search `f5e25b647510`, facial index `3a04dd787a1f`, facial maintenance `c78ce4923f37`, ajuste `88140dcddf8c`, Evolution API `c0db1647bc23`, Evolution DB `de2ca0cf5a16`, Evolution Redis `3112575298ff`, DB `56caed105a12`, Redis `ebfa19d492e5`.
- Terceiros preservados com os mesmos IDs: Firefly bot `9335f5e9077e`, API `f06f36a5ed33`, frontend `6ea8a742b093`, banco `768223c11835`, Nginx Proxy Manager `66c25ca56d8c`, Portainer `e49166611a66`.

### Candidatos e decisão

| Área | Evidência | Decisão |
|---|---|---|
| Checkout: pytest/ruff/pycache, .next, caches npm/Vite, tmp/temp/.codex-tmp | Ausentes nos caminhos examinados; varredura de diretórios de código sem seguir symlinks e excluindo mídia/dados/modelos | Nada a limpar |
| API e worker: `/root/.cache/pip` | Mesmos seis arquivos, 1.020.349 bytes por visão de container; `docker diff` sem alteração nesse caminho, portanto originados na imagem | Preservar: apagar em runtime só cria whiteout, sem recuperar camada do host |
| API/worker/web: `/tmp` | 4 KB em cada container examinado | Preservar, sem benefício comprovado; não inferir descartabilidade de temporários de processo ativo |
| Docker Build Cache | 1.427 registros, 44,24 GB, reportados reclaimable pelo daemon global | Preservar: builder compartilhado, sem prova de exclusividade do projeto; nenhum prune autorizado pelo escopo conservador |
| Imagens Docker | 215 imagens, 13,94 GB; 6,25 GB reportados reclaimable | Preservar: camadas compartilhadas e possível rollback; reclaimable não comprova descarte seguro |
| Containers parados próprios | face-worker `ae6b50513137` e migrate `d974f4306e52`, camada gravável 0 B | Preservar: sem ganho relevante e com utilidade histórica/operacional |
| Volumes/Redis/bancos, mídia, referências faciais, branding, Evolution, backups e deploy-state | Mounts identificados como persistentes; nenhum conteúdo examinado | Exclusão integral do escopo de limpeza |

Resultado: **zero arquivos, imagens, containers ou volumes removidos; zero reinícios e zero mudança de configuração**. O inventário não encontrou alvo exclusivo com benefício que justificasse uma mutação. Não foi necessário solicitar autorização de exclusão vazia. Qualquer ampliação futura ao cache global exige escopo e decisão próprios, pois afeta infraestrutura de terceiros e o projeto proíbe prunes. A negativa automática anterior refere-se ao comando local; não ocorreu tentativa de exclusão remota nem contorno dessa negativa.
