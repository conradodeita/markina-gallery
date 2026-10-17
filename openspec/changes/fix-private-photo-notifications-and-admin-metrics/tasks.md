# Tasks

## 1. Avisos de fotos privadas

- [ ] 1.1 Estender o lote durável por migration preservadora de registros para uma pasta canônica restrita, associar ativos inclusive em retentativas e corrigir o gatilho ao fim do processamento; verificar lotes fechados/abertos, sem prévia, falha parcial, retomada e deduplicação em `backend/tests/test_private_upload_batches.py`.
  - Implementação e testes locais de comportamento concluídos; a suíte CI executou a migration com PostgreSQL. Os dois últimos jobs backend chegaram a 1630 passed e 23 skipped, mas falharam nos testes do contrato histórico 0070: a expectativa de catálogo precisava refletir colunas novas e a mudança de nulidade de `derived_gallery_id` introduzidas na revisão 0082. Ambas foram incorporadas à expectativa em `backend/tests/test_tenant_photographer_migration.py`; rerun integral do CI pendente.
- [x] 1.2 Verificar entregas independentes e autorização no momento do envio; garantir que uploads de pastas públicas não criem evento privado; executar testes direcionados de notificações e vínculo sem chamadas externas reais. Evidência: `pytest tests/test_private_upload_batches.py tests/test_notification_payments.py -q` — 8 passed; upload público sem evento, dois canais habilitados enfileirados, autorização revalidada após revogação e retentativas sem duplicação.

## 2. Indicador de mensagens em Vendas e pagamentos

- [x] 2.1 Remover o KPI agregado legado sem remover retry ou estados atuais por pedido; atualizar `frontend/app/admin/payments/page.test.tsx` e verificar renderização sem o card. Evidência: teste frontend focado passou e confirmou que “Falhas de mensagem” não aparece.
- [x] 2.2 Confirmar que canais desativados/cancelados não aparecem como falhas recuperáveis nos detalhes restantes; atualizar testes de API e executar regressões de projeção/retry de pagamento. Evidência: `pytest tests/test_notification_payments.py -q` — 2 passed; retry e projeção terminal de canal desativado preservados.

## 3. Indicadores da Visão Geral

- [x] 3.1 Ajustar a consulta para contar pastas públicas/privadas de conteúdo com ao menos um `MediaJob` queued/processing e somar todas as fotos cadastradas nelas; cobrir pastas auxiliares, sem job, privadas, públicas, mistas e jobs encerrados nos testes de `/admin/validation-summary`. Evidência: `pytest tests/test_derived_galleries.py::test_admin_validation_summary_counts_active_public_and_private_content_folders -q` — 1 passed.
- [x] 3.2 Atualizar o contrato de dados, os rótulos e o teste do card da Visão Geral para apresentar pastas com importação ativa e total de fotos dentro dessas pastas. Evidência: teste da Visão Geral incluído nos 23 testes frontend aprovados.

## 4. Integração e revisão

- [ ] 4.1 Executar validações focadas backend/frontend, lint, typecheck, build e OpenSpec estrito; registrar evidências e revisar diff/status sem tocar nas alterações locais preexistentes.
  - Evidências locais: 9 testes backend focados passaram; 23 testes frontend focados passaram; Ruff passou; ESLint passou sem erros (31 avisos); TypeScript passou; build Next.js passou; validação estrita desta change passou; Alembic informa `20261016_0082 (head)`. A validação estrita global reportou 29 falhas em outras changes/specs. Dois CIs: frontend, OpenSpec e checks independentes passaram; cada pytest concluiu com 1630 passed e 23 skipped, mas duas asserções nos testes de catálogo histórico 0070 falharam por colunas/nulidade posteriores da revisão 0082. A expectativa foi atualizada e aguarda novo CI. Gitleaks falhou em ambos os CIs por ocorrências em histórico de branches alheias à PR, confirmado em inspeção local.

## Workflow follow-up

- Sincronizar os deltas para as specs principais e arquivar somente após revisão humana, conforme o fluxo OpenSpec do repositório.
