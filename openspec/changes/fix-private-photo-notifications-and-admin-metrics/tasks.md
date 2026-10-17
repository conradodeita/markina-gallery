# Tasks

## 1. Avisos de fotos privadas

- [x] 1.1 Estender o lote durável por migration preservadora de registros para uma pasta canônica restrita, associar ativos inclusive em retentativas e corrigir o gatilho ao fim do processamento; verificar lotes fechados/abertos, sem prévia, falha parcial, retomada e deduplicação em `backend/tests/test_private_upload_batches.py`. Revalidado no grafo reconciliado: CI `39046656588`, backend aprovado com PostgreSQL sintético configurado e suíte integral `1650 passed, 23 skipped`; migration privada `20261017_0083` aplicada após `20261016_0082` pelo deploy do mesmo run. Ver evidências consolidadas em `../reconcile-homolog-release-lineage/validation.md`.
- [x] 1.2 Verificar entregas independentes e autorização no momento do envio; garantir que uploads de pastas públicas não criem evento privado; executar testes direcionados de notificações e vínculo sem chamadas externas reais. Evidência: `pytest tests/test_private_upload_batches.py tests/test_notification_payments.py -q` — 8 passed; upload público sem evento, dois canais habilitados enfileirados, autorização revalidada após revogação e retentativas sem duplicação.

## 2. Indicador de mensagens em Vendas e pagamentos

- [x] 2.1 Remover o KPI agregado legado sem remover retry ou estados atuais por pedido; atualizar `frontend/app/admin/payments/page.test.tsx` e verificar renderização sem o card. Evidência: teste frontend focado passou e confirmou que “Falhas de mensagem” não aparece.
- [x] 2.2 Confirmar que canais desativados/cancelados não aparecem como falhas recuperáveis nos detalhes restantes; atualizar testes de API e executar regressões de projeção/retry de pagamento. Evidência: `pytest tests/test_notification_payments.py -q` — 2 passed; retry e projeção terminal de canal desativado preservados.

## 3. Indicadores da Visão Geral

- [x] 3.1 Ajustar a consulta para contar pastas públicas/privadas de conteúdo com ao menos um `MediaJob` queued/processing e somar todas as fotos cadastradas nelas; cobrir pastas auxiliares, sem job, privadas, públicas, mistas e jobs encerrados nos testes de `/admin/validation-summary`. Evidência: `pytest tests/test_derived_galleries.py::test_admin_validation_summary_counts_active_public_and_private_content_folders -q` — 1 passed.
- [x] 3.2 Atualizar o contrato de dados, os rótulos e o teste do card da Visão Geral para apresentar pastas com importação ativa e total de fotos dentro dessas pastas. Evidência: teste da Visão Geral incluído nos 23 testes frontend aprovados.

## 4. Integração e revisão

- [x] 4.1 Reexecutar CI integral e validar o grafo Alembic reconciliado (`20261017_0083` como head) após integrar a base atualmente instalada em homologação. PR #210 integrada em `c9eaf638`; CI `39046656588` aprovado no alvo `25cd338`, com backend, frontend, Gemma, OpenSpec, Gitleaks e política de homologação verdes. Deploy e inventário `39049112709` confirmaram schema 0083 e saúde HTTP 200.
- [x] 4.2 Classificar e suprimir somente os quatro falsos positivos históricos do Gitleaks por fingerprint exato, mantendo a varredura do histórico completo; confirmar Gitleaks local e CI. Evidências: Gitleaks 8.24.3 encontrou zero findings localmente; o check Gitleaks do CI `39023880662` passou. Os quatro fingerprints correspondiam a APP_VERSION/SHA, checksums de arquivos e fingerprint de configuração em documentos de evidência.

## Workflow follow-up

- Sincronizar os deltas para as specs principais e arquivar somente após revisão humana, conforme o fluxo OpenSpec do repositório.
- Conferência de continuidade em 17/10/2026 neste chat sucessor: versão funcional `25cd338` publicada, checkout remoto limpo, serviços Markina saudáveis e `/api/health` com resposta saudável. PR #214 integrada apenas para registrar a evidência do probe/deploy; seu CI de PR `39049217618` passou. O CI pós-merge `39051577413` ainda estava em andamento na conferência; ele não é evidência de uma nova publicação. Não houve disparo de mensagens reais, novo deploy, migration ou alteração de configuração nesta conferência. A entrega real de WhatsApp/push não foi revalidada nesta retomada.
