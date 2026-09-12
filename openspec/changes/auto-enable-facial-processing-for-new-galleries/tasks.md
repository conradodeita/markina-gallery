## 1. Contratos de regressão

- [ ] 1.1 Adicionar testes da resolução de rollout para galeria ativa sem registro individual, flag desligada, galeria inativa, calibração de produção ausente e estados explícitos; verificar que a precedência corresponde à delta spec.
- [ ] 1.2 Adicionar testes do payload administrativo e da admissão de indexação para galeria sem rollout; verificar `active/general` no painel e criação idempotente do job quando as prévias estiverem prontas.

## 2. Disponibilidade facial geral

- [ ] 2.1 Alterar a resolução de disponibilidade para considerar galeria ativa sem rollout individual como habilitada quando kill switch e calibração permitirem; verificar que rollouts explícitos não são contornados.
- [ ] 2.2 Ajustar o payload de estado para representar a disponibilidade implícita como `active/general`; verificar que ausência indisponível continua `unavailable` e que etapas persistidas são preservadas.

## 3. Validação e entrega

- [ ] 3.1 Executar testes backend focados de rollout, status e indexação, Ruff, OpenSpec estrito e `git diff --check`; revisar o diff para confirmar ausência de migration, mutação em massa e reprocessamento de mídia.
- [ ] 3.2 Preparar inventário de impacto zero e solicitar autorização humana específica antes de push, merge e deploy em homologação; após autorização, validar SHA, migration, workers, flags e healthchecks.
