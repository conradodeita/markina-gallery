# Diagnóstico administrativo de capacidade

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

## Requisitos antes de expansão

SLOs gerais e esquema métrico precisam de aprovação; carga mista PostgreSQL/API, jornadas e bytes/egress requerem evidência nos estudos B05/B06/B11 em ambiente isolado e autorizado. Este diagnóstico sozinho não promete capacidade, disponibilidade, preço ou escala. P0.2 fairness/quotas e suporte a vários fotógrafos são escopos separados.
