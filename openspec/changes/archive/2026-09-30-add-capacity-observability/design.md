# Design

## Context

Ver [proposal.md](proposal.md) e [delta spec](specs/deployment-operations/admin-capacity-diagnostics/spec.md). Inspeção documental na base `abd4d21f8fec1efd0f18eb0a8eebe4c0f2444293`; nenhum valor abaixo representa medição de runtime nesta entrega.

| Fonte inspecionada | Fato no código e consequência |
|---|---|
| `backend/app/auth.py`, engine e `SessionLocal` | Um engine por processo importador, sem parâmetros explícitos de pool. Defaults da biblioteca não são ocupação medida nem inventário dos processos ativos. |
| `backend/app/main.py`, `require_admin`, `db_session`; `backend/app/tenancy.py` | Sessão persistida, papel admin, vínculo ativo e exatamente uma conta ativa na instalação. O diagnóstico usa a mesma autoridade. |
| `backend/app/facial/observability.py` e `GET /admin/facial-observability` | Admissões em memória são locais ao processo; coletor carrega todos os jobs/consultas concluídas; idade atual inclui `queued` e `processing`; dimensões faciais limitadas a `environment/type/state`. Não serve diretamente ao novo contrato limitado. |
| `backend/app/facial/capacity.py` | Já usa `COUNT`/`MIN`, mas mede pressão de busca incluindo processamento. Reutilizar o padrão de agregação, não atribuir a ele a semântica de espera pura. |
| `backend/app/facial/jobs.py` | Fonte durável é SQL; classes são search, index e maintenance (purge/cleanup). `available_at` controla agendamento; lease vencido permite recuperação. Redis apenas sinaliza. |
| `backend/app/worker.py` | Mídia filtra análise pending/receiving antes de claim; o loop contém mensagens e manutenção com regras diferentes. Não há uma única fila global. |
| `backend/app/preview_adjustment/service.py`, `PreviewAdjustment` | Ajuste guarda `updated_at`, sem `created_at`/`queued_at`; configurações/generation/fingerprint são revalidados durante execução. Idade desde atualização é somente aproximação. |
| `frontend/app/admin/page.tsx`, `frontend/app/ui-kit.tsx` | Visão geral usa resumo com contagens, storage e galerias recentes; há componentes de card/estado reutilizáveis e nenhum painel de observabilidade facial encontrado. |
| `docker/docker-compose.yml`, override de ajuste, `backend/Dockerfile`, `backend/migrations/env.py` | Há API, worker geral, classes faciais e ajuste opcional. Dockerfile usa Uvicorn sem `--workers`; Alembic abre outro engine com `NullPool`. Topologia versionada não comprova processos ativos, overrides ou reservas operacionais. |

### Reconciliação com mudanças ativas

`openspec list --json` identifica changes ainda ativas, muitas com somente aceite operacional pendente. Esta proposta não as conclui nem usa checkboxes históricos como prova remota.

- `add-tenant-ownership-foundation`: fundação já presente na base, com guardas de instalação única; suas pendências de entrega/sync ficam com o fluxo responsável. Não habilitar segunda conta ou collector global entre fotógrafos.
- `productionize-facial-search` e `integrate-private-facial-filter`: preservar allowlists, limites faciais, backpressure e gates de produção. Não renomear métricas existentes nem promover seus limiares a SLOs gerais.
- `evolve-highres-facial-pipeline` e `folder-processing-settings`: preservar dependências de análise, pausa por pasta e revalidação antes de processar. Diagnóstico não chama funções de preparação, claim ou reconciliação.
- `add-optional-preview-auto-adjustment`: worker opcional independente; fila vazia ou acumulada não prova que o worker está ligado/desligado.
- `add-storage-usage-and-reset-homolog` e `add-visual-validation-surfaces`: reaproveitar a Visão geral, mantendo os contratos de resumo/storage. Autorizações históricas de limpeza não se aplicam aqui.
- Correções de lifecycle/clientes e entrega da base permanecem intocadas. CI/deploy e limpeza conduzidos em outro chat não são dependência desta preparação local.

## Goals / Non-Goals

**Goals:** projeção aditiva de baixo custo, sem leituras de conteúdo sensível; métricas com origem e limitações auditáveis; falha parcial sem interromper o painel; implementação reversível sem alteração de schema.

**Non-Goals:** instrumentação distribuída, histórico de métricas, descoberta Docker/SSH, inventário remoto automático, total de toda a aplicação, tuning e conclusão de P0.3. O contrato mínimo deste diagnóstico precisa de aceite; o esquema métrico amplo, SLOs gerais e orçamento global continuam decisões de futuras changes.

## Decisions

### 1. Endpoint dedicado e painel existente

Criar `GET /admin/capacity-observability`, sem parâmetros de tenant, consulta SQL, filtros livres ou seleção de servidor. O browser acessa `/api/admin/capacity-observability` pelo encaminhamento existente. Reutilizar `require_admin` antes da coleta/cache e o contexto único; não converter falha de autenticação/ownership em resposta parcial de métricas. Autorização negada mantém 403; impossibilidade de verificá-la por infraestrutura retorna erro sanitizado sem diagnóstico. A sessão de coleta reutiliza o engine existente, com leitura apenas.

Na `/admin`, seção inicialmente recolhida, `SurfaceCard`, `SystemState`, badges neutros e botão “Atualizar diagnóstico”. Buscar na primeira abertura e em atualização manual, uma requisição por vez; abortar ao desmontar e limpar snapshot se perder autorização. Se uma atualização falhar, sinalizar a falha e não manter o snapshot anterior com aparência de coleta atual; os instantes originais permanecem visíveis enquanto um snapshot for exibido. Nenhum polling, download/exportação, localStorage, nova entrada de menu ou ação de ajuste de capacidade.

Alternativas: anexar a `/admin/validation-summary` somaria custo à abertura habitual e acoplaria uma saída de capacidade a galerias com nomes/IDs. Estender `/admin/facial-observability` misturaria domínios e obrigaria refatoração de histórico fora deste recorte. O novo endpoint reutiliza padrões e a tela existente, isolando o custo e o rollback.

### 2. Contrato mínimo de evidência

Usar schema tipado e serialização por allowlist, sem dicionários arbitrários provenientes do driver. Envelope proposto:

| Campo | Semântica |
|---|---|
| `schema_version` | Literal `1`, contrato deste snapshot, não esquema completo de P0.3. |
| `collection_started_at`, `collection_finished_at` | UTC ISO 8601 com `Z`; janela real da coleta. |
| `cached` | Reuso em memória, sem atualizar instantes da coleta. |
| `database`, `pool`, `queues`, `connection_budget` | Seções independentes e com valores indisponíveis explícitos. |
| `coverage`, `limitations` | Listas fechadas de categorias cobertas e lacunas; sem texto livre do ambiente. |

Cada valor numérico possui `value`, `unit` (`connections`, `jobs`, `seconds`), `evidence` (`observed`, `calculated`, `estimated`, `unavailable`), `scope` (`responding_api_process`, `application_database`, `postgresql_server`), `source`, `collected_at`, `reason`. Fonte, motivo, classe e estado são enums estáveis. Indisponível implica `value=null`; dado ausente por fila vazia usa motivo `empty_queue`, distinto de falha da consulta. Inteiros para contagens, segundos finitos e não negativos para duração. Timestamps brutos de cada job não são expostos; somente idade agregada.

Contagens e configuração efetiva lida são observadas; soma de tetos finitos ou diferença entre instantes é calculada; idade utilizada como aproximação de espera é estimada. Registrar a base temporal como enum, sem texto de registro. Instantes futuros inconsistentes não produzem idade negativa: marcar idade indisponível com motivo `inconsistent_timestamp`, preservando contagem válida.

Não reusar o schema `FacialMetricSample` para acrescentar dimensões: manter `ALLOWED_DIMENSIONS` e seu validador intactos. Reutilizar a disciplina de allowlists e sanitização em schema próprio. Não incluir aqui os contadores de admissões do processo, percentis antigos ou alertas faciais, pois não são necessários ao recorte.

### 3. Conexões e limites de pool sem inferência global

Consultar exclusivamente o PostgreSQL já usado pelo engine, sem nova credencial, novo banco ou extensão. Usar agregação em `pg_stat_activity` de `backend_type = 'client backend'`: uma projeção para o banco atual e outra para o servidor conectado, com grupos fixos `active`, `idle`, `idle_in_transaction`, `other`, `unknown`. Contagem do banco atual é subconjunto da contagem do servidor; não somar as duas. Outras identidades/bancos/usuários não são enumerados. A própria conexão da coleta está incluída e isso aparece nas limitações.

Ler somente `max_connections`, `superuser_reserved_connections` e `reserved_connections`, este último quando suportado; ausência não vira zero. Estados ocultos por privilégios entram em `unknown`, sem tentar elevar permissões. Se a visibilidade não permitir sequer classificar os backends e garantir a contagem completa, o total afetado fica indisponível; nunca apresentar subconjunto visível como total do servidor. Falha do total ou configuração gera indisponibilidade do campo. Não ler colunas de SQL, endereço, nome de aplicação ou identidade, nem executar `pg_stat_statements`, `EXPLAIN ANALYZE`, inspeção de logs ou extensões.

Para o pool respondente, adaptador pequeno de leitura do objeto já criado: tipo permitido, tamanho configurado, máximo de overflow, timeout configurado, checked-in e checked-out. Se for QueuePool com teto finito, `potential_max = size + max_overflow`, calculado; total aberto local pode ser calculado como checked-in + checked-out, explicitando que são leituras próximas e não atômicas. `overflow()` pode ser negativo antes de encher o pool e não é métrica de conexões abertas; não publicá-lo cru. Não chamar `connect()` para preencher ou aquecer pool.

SQLAlchemy não oferece accessor público uniforme para todos os limites. Encapsular qualquer introspecção dependente da versão (por exemplo máximo de overflow) num adaptador testado; campo sem acesso seguro fica indisponível, sem fixar 5/10/30 como runtime observado. `size=0`, overflow ilimitado, NullPool e outros pools exigem indicação de semântica não finita/não suportada. Não usar um default da biblioteca como substituto silencioso.

`pool_wait_seconds` e `pool_timeouts_total` ficam indisponíveis por ausência de instrumentação neste recorte. Timeout configurado não é espera medida, e duração da consulta não mede aquisição. Ocupação dos pools dos workers fica indisponível; não registrar agentes por worker nem coletar processos do host.

Alternativa rejeitada: impor pools explícitos ou interceptar todas as sessões para obter espera. Isso altera a operação/escopo e exige orçamento, métricas e testes próprios de P0.3.

### 4. Inventário e orçamento: lacuna explícita

Neste recorte `connection_budget.status=unavailable`, `potential_connections=null`, `budget_headroom=null`. Motivos fixos incluem `process_inventory_missing`, `external_consumers_unknown` e `operational_reserve_unapproved`. Nenhuma API de edição/importação do inventário é criada. A documentação da implementação incluirá este modelo para um futuro inventário autorizado:

| Grupo a inventariar | O que registrar por processo/engine, sem host/DSN/segredo |
|---|---|
| API | Número real de processos/réplicas, engines por processo, classe/tamanho/overflow, fonte e UTC. |
| Worker geral | Processos e pools reais; várias funções no mesmo processo podem compartilhar o mesmo engine, sem contar um pool por tipo de job. |
| Facial search/index/maintenance | Cada classe separadamente, inclusive processos ociosos, paralelos ou desligados confirmados. |
| Ajuste opcional | Perfil/ativação e processos realmente existentes; ausência de jobs não comprova ausência de processo. |
| Migration/seed/manutenção | Concorrência máxima autorizada e conexão direta/NullPool; engine importado mas sem conexão não equivale a pool saturado. |
| Administração/backup/outros consumidores | Picos e reservas explícitos no mesmo servidor PostgreSQL; consumidores de outro servidor não entram neste orçamento. |
| Reservas | Slots PostgreSQL reservados e reserva operacional adicional aprovada, distinguindo-os dos consumidores já contados. |

Fórmula documental, não calculada pela API nesta entrega: `C_aplicacao = soma(processos_confirmados * teto_finito_por_engine) + pico_conexoes_pontuais`. `C_utilizavel = max_connections - reservas_tecnicas`. Verificar `C_aplicacao + C_outros_consumidores + reserva_operacional < C_utilizavel`, sem descontar reservas duas vezes, sem somar ocupação observada ao teto dos mesmos pools e sem ignorar pools ilimitados. Quantidade desconhecida, reserva não aprovada, engines omitidos ou inventário fora da janela pertinente invalidam o total; não produzir total parcial com rótulo global.

Mesmo um orçamento completo não demonstra throughput, latência, segurança de réplicas ou SLA. B05 (carga PostgreSQL com pools/processos inventariados), B06 (API/jornadas) e B11 (bytes/egress) permanecem ensaios futuros autorizados separadamente, nunca no host compartilhado por iniciativa desta change.

### 5. Filas: cinco classes, sem executar o scheduler

Consultas agregadas retornam somente contagens e mínimos temporais para estados abertos, sem carregar objetos ORM completos. Usar uma referência UTC por coleta e critérios do código inspecionado, sem refatorar os workers.

| Classe fixa | Contagens e base de idade | Limites da interpretação |
|---|---|---|
| `media` | `queued_total`, `processing_total`; `blocked_dependency_total` para análise pending/receiving; `claim_candidates_total` = queued após esse filtro; `oldest_record_age_seconds` sobre created_at dos candidatos. | Idade desde criação é calculada; como espera é estimativa e pode incluir tentativas anteriores. Candidato após filtro não garante publicação: `media_can_proceed` revalida depois. |
| `preview_adjustment` | queued e processing; idade desde menor updated_at dos queued. | Espera estimada desde última atualização. Espera exata, candidatos executáveis e agendamento ficam indisponíveis; configuração/generation/arquivos podem invalidar o registro durante execução. Não acessar filesystem nem configuração com lock. |
| `search`, `index`, `maintenance` | `queued_total`; `scheduled_total` para available_at futuro; `claim_candidates_total` para queued com available_at vencido; `processing_total`; subconjunto `reclaimable_total` para processing com lease vencido e available_at vencido. | Reclaimable permanece subconjunto de processing, nunca somado como trabalho adicional. Contagens não provam consumidores ativos. |

Para facial, expor idade desde criação dos candidatos e `oldest_due_age_seconds = agora - min(available_at)` dos queued vencidos. O segundo é cálculo de tempo desde o agendamento persistido; sua interpretação como espera da tentativa atual é estimada, pois retries/reclaims não mantêm histórico completo de espera/serviço. Manutenção agrega somente purge e cleanup usando o mapa de classes existente. Jobs terminais não participam; processing não participa das idades de queued. Idade sem nenhum candidato retorna null/empty_queue, contagem zero. `queued_total = scheduled_total + claim_candidates_total` quando todos os timestamps válidos permitem classificar; inconsistência temporal deve ser indicada.

No caso de mídia, não reclassificar failed/processing recuperáveis como queued antes de o worker fazê-lo. No ajuste, não converter updated_at em created_at imaginário. Não derivar tempo exato de espera, ETA, taxa de serviço ou p95 de `updated_at-created_at`.

Cobertura omitida explícita: WhatsApp/OTP, e-mail, entregas push/WhatsApp, outboxes legadas/faciais, lifecycle/exclusões e limpeza de arquivos/privacidade. Essas etapas podem referir-se ao mesmo trabalho de negócio e não devem ser somadas a jobs de mídia/facial. Ampliação exige reconciliação dos contratos em outra revisão. A idade das filas cobertas é útil para o primeiro diagnóstico sem prometer uma visão completa do worker geral.

### 6. Orçamento de coleta e degradação

Proposta de proteção interna do novo coletor: cache de até 30 segundos por processo, incluindo resultados parciais; uma coleta em andamento por processo; lock sem espera prolongada. Requisição autorizada concorrente recebe snapshot ainda válido ou resposta sanitizada `collection_busy`. Cache expirado não é apresentado como atual. Reinício perde o cache; não há cache compartilhado, persistência, série temporal ou retenção adicional.

Cada coleta faz no máximo oito SELECTs diagnósticos agregados, independentemente da quantidade de jobs: configurações PostgreSQL, conexões, mídia, ajuste e classes faciais cabem nesse teto. Autenticação e guardas existentes não integram esse contador. Máximo de cinco linhas de classes de fila e grupos de conexão fixos; nenhum `SELECT *`, N+1, histórico terminal ou retorno truncado apresentado como total. Agregação limita resultado, mas não o custo de scan: usar timeout e verificar planos em PostgreSQL sintético antes de concluir implementação.

Em PostgreSQL, leitura em transações curtas com `SET TRANSACTION READ ONLY`, `SET LOCAL statement_timeout` de no máximo 500 ms por consulta e `SET LOCAL lock_timeout` de no máximo 100 ms, usando o tempo restante de um orçamento de dois segundos para coleta após adquirir conexão. Configurar a transação antes de qualquer SELECT nela, inclusive guardas, preservando a autorização prévia em sua sessão existente. São limites propostos da nova rotina, não novos defaults do servidor/pool ou SLOs de produto. Não emitir novas consultas após o prazo; cancelar/rollback em timeout, sem deixar configuração vazar para outra sessão. Falha em configurar a proteção impede a consulta afetada. Usar transações isoladas por seção ou rollback antes da seguinte para que falha PostgreSQL não invalide todas as seções.

Aquisição do engine e validação da sessão continuam sujeitas aos timeouts existentes; o prazo de dois segundos não é promessa de latência HTTP total. Não trocar `pool_timeout` nem abrir engine alternativo para contornar saturação. Se aquisição falhar, retornar estado sanitizado sem retry em loop. Guardas vêm antes do cache; eles também dependem do banco e podem impedir toda a resposta.

SQLite serve aos testes de contrato e marca métricas PostgreSQL como não suportadas; limites de execução SQL serão comprovados em PostgreSQL sintético descartável, não presumidos pelo sucesso de SQLite. Não conceder permissões, instalar extensão, alterar índice/schema ou rodar carga remota se uma consulta não couber: registrar a seção indisponível e revisar a solução.

Resposta com `Cache-Control: no-store`; nenhum service worker deve armazená-la. Logs têm apenas categorias como `query_timeout`, `permission_denied`, `unsupported_backend`, `unsupported_pool`, `collection_busy`, `inconsistent_timestamp` e `source_unavailable`, sem exceções brutas, SQL ou parâmetros. Validação de saída por allowlist inclui fonte/reason/labels; não serializar objeto de pool ou conexão. Não criar auditoria com conteúdo do snapshot nem registrar cada atualização como ação crítica de domínio.

## Risks / Trade-offs

- [Idade confundida com espera real] → rótulos distintos para idade calculada/espera estimada, explicação visível e testes com retries, agendamento futuro e processing.
- [Snapshot confundido com capacidade comprovada] → orçamento nulo, lacunas explícitas, sem recomendação de réplicas/usuários ou semáforo SLO.
- [Agregação onerosa] → escopo de estados abertos, teto de consultas/tempo, cache curto, planos sintéticos; indisponibilidade em vez de aumentar privilégios/limites.
- [Instalação com conta extra após cache] → revalidar sessão/vínculo e guarda antes de responder; preservar falha fechada.
- [Informação sensível em driver/registro] → projeções numéricas no DB, schema fechado, erros neutros e teste com strings sentinela sensíveis.
- [Introspecção do pool dependente da biblioteca] → adaptador isolado, testes da versão usada, indisponível em tipos não suportados.
- [Coleta ocupa conexão] → incluir a própria coleta no escopo explicado, reusar engine e liberar rapidamente; não alegar leitura sem qualquer custo.
- [Cobertura parcial de filas] → lista visível do que foi coberto e omitido; não somar cinco classes como total geral de trabalho.

## Migration Plan

1. Após aceite humano, implementar e validar tasks locais com dados sintéticos, sem mudança de schema, ambiente ou recursos existentes.
2. Preparar documentação de operação com significado dos campos, inventário ainda faltante, custo observado em teste e limitações; o teste local não aprova capacidade real.
3. Entregar diff/evidências para revisão. Publicação e deploy exigem nova autorização com inventário atual de serviços, portas/subdomínio, versão exata e plano de impacto zero; não reutilizar autorização de outro chat.
4. Reversão de código retira a seção/endpoint sem desfazer migrations ou alterar dados/pools. Confirmar compatibilidade dos endpoints preexistentes. Não executar downgrade, restore ou limpeza.
5. Sincronizar a nova spec e arquivar apenas após implementação validada e revisão humana conforme o fluxo do repositório.

## Review

Decisões propostas para aceite: endpoint separado com seção no painel existente; schema mínimo e cinco classes de fila; cache e proteção de consulta locais; orçamento global indisponível até inventário externo completo. A proposta não depende de escolher agora um SLO geral, definir reservas numéricas nem medir o servidor. Essas decisões pertencem à continuação de P0.3, com aprovação do esquema métrico amplo e evidência operacional própria.
