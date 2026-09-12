## 1. Contratos de regressão

- [x] 1.1 Adicionar testes da resolução de rollout para galeria ativa sem registro individual, flag desligada, galeria inativa, calibração de produção ausente e estados explícitos; verificar que a precedência corresponde à delta spec. Evidência: os contratos cobrem todos os ramos e reproduziram a única divergência do código anterior na ausência de rollout; o bloqueio explícito passou.
- [x] 1.2 Adicionar testes do payload administrativo e da admissão de indexação para galeria sem rollout; verificar `active/general` no painel e criação idempotente do job quando as prévias estiverem prontas. Evidência: os contratos reproduziram o payload `unavailable` e a recusa indevida do job no código anterior, sem falhas fora do comportamento-alvo.

## 2. Disponibilidade facial geral

- [x] 2.1 Alterar a resolução de disponibilidade para considerar galeria ativa sem rollout individual como habilitada quando kill switch e calibração permitirem; verificar que rollouts explícitos não são contornados. Evidência: resolução valida flag, calibração e galeria ativa antes do padrão geral; contratos de `prepared`, `active`, `suspended` e `revoked` passaram.
- [x] 2.2 Ajustar o payload de estado para representar a disponibilidade implícita como `active/general`; verificar que ausência indisponível continua `unavailable` e que etapas persistidas são preservadas. Evidência: payload implícito passou para os estados disponível e indisponível, preservando `active/canary` persistido.

## 3. Validação e entrega

- [x] 3.1 Executar testes backend focados de rollout, status e indexação, Ruff, OpenSpec estrito e `git diff --check`; revisar o diff para confirmar ausência de migration, mutação em massa e reprocessamento de mídia. Evidência: 33 testes de rollout, status, indexação e busca passaram; Ruff, OpenSpec estrito e `git diff --check` aprovados; diff sem migration, mídia, jobs retroativos ou escrita em massa.
- [x] 3.2 Preparar inventário de impacto zero e solicitar autorização humana específica antes de push, merge e deploy em homologação; após autorização, validar SHA, migration, workers, flags e healthchecks. Evidência: PR #69 integrada em `develop`; workflow `34661773053` publicou o SHA `43c0d017ffdcc8891da24be31d770b957dbc2b41`; migration permaneceu em `20260910_0053 (head)`; flag facial permaneceu ativa; os workers de indexação, busca e manutenção ficaram saudáveis; `/healthz`, `/api/health` e a galeria pública responderam HTTP 200.
