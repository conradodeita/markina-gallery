# Diagnóstico administrativo de capacidade

## Acesso do dono da instalação

Na implementação local da change `add-small-multi-photographer-pilot`, o monitor global exige permissão explícita e revogável do operador da instalação. Ser fotógrafo não concede esse acesso. A permissão não permite acessar clientes, fotos ou pedidos de outros fotógrafos. Migration/seed não a concedem automaticamente; o operador é identificado e autorizado no pacote operacional antes do provisionamento offline descrito em `openspec/changes/add-small-multi-photographer-pilot/provisioning.md`. Esta documentação não afirma que a versão já foi publicada.

A Visão geral consulta a capability do backend e mostra **Capacidade e filas** somente após autorização positiva. Ao voltar à aba, revalida a capability e descarta o snapshot anterior; isso não coleta métricas automaticamente. Se detectar logout, revogação ou HTTP 401/403, remove painel e cópia. Falha na consulta da capability mantém o monitor oculto. O diagnóstico comercial do fotógrafo continua limitado à própria conta.

## Escopo e leitura

O diagnóstico é uma amostra sob demanda obtida em `GET /api/admin/capacity-observability`. Cada valor traz escopo, fonte, UTC, unidade e classe de evidência (`observed`, `calculated`, `estimated` ou `unavailable`). `cached=true` indica reutilização por até 30 segundos no mesmo processo da API; timestamps descrevem a coleta original. O snapshot não representa transação atômica entre PostgreSQL, pool e filas.

- `database`: sessões `client backend` agregadas para o banco conectado e para o servidor PostgreSQL. A contagem do banco já está dentro da do servidor; não somar. As conexões dessa consulta aparecem na amostra. `max_connections`, `superuser_reserved_connections` e `reserved_connections` são settings, não capacidade disponível por si.
- `pool`: somente o processo API que respondeu. `base_size`, `max_overflow` e `potential_max` são limites locais lidos/calculados; `checked_in` e `checked_out` descrevem o pool durante a amostra. `open_connections_estimate` combina leituras próximas. `wait_seconds` e `timeout_count` permanecem indisponíveis porque a aplicação não coleta esses eventos.
- `queues`: mídia, ajuste de prévias, busca facial, indexação facial e manutenção facial, contadas de suas tabelas PostgreSQL. `claim_candidates_total` aplica apenas os filtros reproduzíveis no momento da consulta. `processing_total` é separado. `reclaimable_total` é subconjunto do processamento, não outra fila.
- `connection_budget`: permanece indisponível sem inventário atual de todos os processos/engines/pools, concorrências pontuais, consumidores do mesmo PostgreSQL e reservas aprovadas. O endpoint não calcula margem nem trabalhadores seguros.
- `coverage` e `limitations`: enumera cinco classes medidas e ressalvas. OTP/WhatsApp, e-mail, push/outboxes, lifecycle e limpezas não estão cobertos; portanto, nenhuma soma representa trabalho global de todos os workers.

## Semântica de fila

Mídia persiste `created_at`: sua idade é uma aproximação da espera e pode incluir retries. Ajuste de prévia não persiste `created_at`/`queued_at`; a idade desde `updated_at` é uma estimativa e não prova elegibilidade, pois configuração, geração e fingerprint são revalidados pelo worker. Jobs faciais distinguem `available_at` futuro, aguardando elegível pelo agendamento, processamento e lease expirado. A idade desde o agendamento não mede a duração da tentativa corrente. Nenhuma classe fornece ETA, taxa de serviço, p95 ou prova de que worker esteja ativo.

## Limites da coleta

A coleta usa agregações de saída limitada e somente leitura, máximo de oito SELECTs diagnósticos, statement timeout de até 500 ms por consulta e prazo de até dois segundos após obter conexão. Isso protege a rotina; não é um SLO HTTP nem limita o tempo de aquisição do pool. Cada seção pode ficar indisponível sem substituir falha por zero. Respostas usam `Cache-Control: no-store`; erros e logs têm categorias sanitizadas, nunca texto de driver/SQL.

Em validação local sintética de 2026-09-30, um PostgreSQL 17 efêmero em loopback recebeu 320 jobs de mídia, 32 estados de análise, 240 ajustes e 480 jobs faciais. O coletor executou cinco SELECTs agregados, manteve cinco classes de fila na saída e concluiu a rodada final medida em 0,110 segundo. Os cinco planos foram aceitos pelo `EXPLAIN (FORMAT JSON)`; também foram comprovados statement timeout, lock timeout, rollback/liberação e restauração de `transaction_read_only`, `lock_timeout` e `statement_timeout` ao reutilizar a conexão. Essa duração descreve apenas o corpus e a máquina sintéticos: não é benchmark, capacidade de produção nem SLO.

O orçamento futuro pode usar `C_aplicacao = soma(processos confirmados * teto finito por engine) + pico de conexões pontuais` e `C_utilizavel = max_connections - reservas técnicas`. A condição é `C_aplicacao + C_outros_consumidores + reserva_operacional < C_utilizavel`; reservas não podem ser descontadas duas vezes. Pools sem limite, consumidores desconhecidos ou inventário fora de data invalidam o resultado global. Esta change não faz tal cálculo.

Na Visão geral administrativa, a seção começa recolhida e consulta somente quando aberta. Não há atualização automática; a pessoa administradora pode atualizar manualmente. Uma falha de rede ou autorização remove o snapshot anterior da tela. Valores zero observados são mostrados como zero; campos indisponíveis preservam o motivo, e cada valor mostra a classe de evidência. A interface usa botões nativos para teclado e uma grade que se adapta a telas estreitas.

## Leitura durante o uso por vários fotógrafos

1. Com permissão de operador, abra **Visão geral → Consultar diagnóstico** antes do uso e confira UTC, cache, cobertura e limitações.
2. Durante o uso, clique **Atualizar agora** e observe filas aguardando, em processamento e idades; zeros observados e indisponibilidade têm significados distintos. Cache de até 30 segundos pode devolver a coleta anterior.
3. Ao terminar, atualize e copie outra leitura. Compare os três momentos com o horário e as ações realizadas, quantidade aproximada de fotógrafos/clientes simultâneos e jobs que terminaram ou ficaram pendentes.
4. Para pedir análise neste chat, cole os relatórios completos `capacity-report/v1` e descreva os momentos e sintomas. Não inclua telefone, nome de clientes, imagens, links de convite, OTP ou credenciais. O relatório já traz somente agregados sanitizados.

O monitor não mede clientes simultâneos automaticamente nem identifica qual fotógrafo gerou a fila. Uma fila crescente em amostras repetidas é um sinal a investigar; não prova por si só saturação ou falha de worker. Os três momentos não substituem série histórica ou teste de carga. O ensaio pequeno só será executado após prontidão registrada e, em homologação, autorização própria.

## Copiar relatório para análise

Depois de uma consulta bem-sucedida, **Copiar relatório** coloca na área de transferência uma representação Markdown `capacity-report/v1` do mesmo snapshot que está na tela. A ação não atualiza o diagnóstico, não chama outro endpoint e não envia o conteúdo para nenhum serviço. Para compartilhar a leitura com uma pessoa ou ferramenta de análise, copie o relatório e cole-o explicitamente no canal autorizado.

O formato usa valores e enums do contrato, sem localização, para evitar ambiguidade de separador decimal ou tradução. Ele contém `schema_version`, início e fim UTC da coleta, `cached`, configurações e ocupação do pool respondente, conexões agregadas do PostgreSQL, as cinco filas cobertas, orçamento global, cobertura e limitações. Cada métrica preserva `value`, `unit`, `evidence`, `scope`, `source`, `collected_at` e `reason`; indisponibilidade permanece `value=null` com motivo e nunca vira zero.

Exemplo reduzido da sintaxe, sem substituir o relatório completo:

```text
# Relatório de capacidade e filas

- report_format: capacity-report/v1
- schema_version: 1

## Coleta
- collection_started_at: 2026-09-30T10:00:00Z
- collection_finished_at: 2026-09-30T10:00:01Z
- cached: false

## Pool da API
- checked_out: value=1 | unit=connections | evidence=observed | scope=responding_api_process | source=sqlalchemy_pool | collected_at=2026-09-30T10:00:00Z | reason=null
- wait_seconds: value=null | unit=seconds | evidence=unavailable | scope=responding_api_process | source=none | collected_at=2026-09-30T10:00:00Z | reason=field_unavailable

## Filas
### media
- queued_total: value=0 | unit=jobs | evidence=observed | scope=application_database | source=media_job | collected_at=2026-09-30T10:00:00Z | reason=null
- oldest_record_age_seconds: value=4.5 | unit=seconds | evidence=estimated | scope=application_database | source=media_job | collected_at=2026-09-30T10:00:00Z | reason=null
```

O serializador usa uma lista fechada e ignora propriedades adicionais; não inclui SQL, nomes de banco, usuário ou host, IP, DSN, caminhos, identificadores de negócio, dados pessoais, fotos, tokens, mensagens ou biometria. O texto só existe quando o navegador atende ao gesto de cópia; o produto não o persiste, não cria arquivo nem mantém histórico. Se o navegador negar a área de transferência, a interface informa a falha e mantém o snapshot para nova tentativa. Se a autorização administrativa for perdida, o snapshot e a ação desaparecem.

O relatório continua sendo uma leitura agregada da instalação. Ele não separa dados por fotógrafo, não mede séries históricas, não cria alertas e não comprova throughput, capacidade futura ou cumprimento de SLO.

## Requisitos antes de expansão

SLOs gerais e esquema métrico precisam de aprovação; carga mista PostgreSQL/API, jornadas e bytes/egress requerem evidência nos estudos B05/B06/B11 em ambiente isolado e autorizado. Este diagnóstico sozinho não promete capacidade, disponibilidade, preço ou escala. P0.2 fairness/quotas é escopo separado; suporte a vários fotógrafos depende da prontidão e operação autorizada da change `add-small-multi-photographer-pilot`.
