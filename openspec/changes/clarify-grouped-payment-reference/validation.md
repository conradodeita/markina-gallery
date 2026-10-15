# Validação

## Evidência local

- `pytest -q tests/test_payment_templates.py tests/test_notification_settings.py tests/test_notification_payments.py tests/test_unified_checkout.py` — 26 passed, 3 skipped.
- `pytest -q tests/test_payment_templates.py tests/test_notification_settings.py::test_payment_legacy_api_delegates_to_the_single_source tests/test_unified_checkout.py::test_admin_scope_history_decisions_and_correction tests/test_notification_payments.py::test_payment_decisions_unique_and_correction_silent` — 8 passed.
- `pytest -q tests/test_unified_checkout.py::test_admin_scope_history_decisions_and_correction` — 1 passed após reforçar asserções dos códigos retornados e mensagens agrupadas.
- `pytest -q tests/test_payment_templates.py tests/test_notification_settings.py::test_payment_legacy_api_delegates_to_the_single_source` — 5 passed.
- `pytest -q tests/test_payment_templates.py tests/test_notification_settings.py::test_payment_legacy_api_delegates_to_the_single_source tests/test_unified_checkout.py::test_admin_scope_history_decisions_and_correction` — 6 passed após incluir a prévia do aviso enviado ao fotógrafo.
- `npm test -- --run app/admin/payments/payment-actions.test.tsx app/admin/payments/page.test.tsx app/admin/notifications/page.test.tsx` — 24 passed.
- `npx tsc --noEmit` — passou.
- `npx eslint app/admin/payments/page.tsx app/admin/payments/page.test.tsx app/admin/payments/payment-actions.tsx app/admin/payments/payment-actions.test.tsx app/admin/notifications/page.tsx app/admin/notifications/page.test.tsx` — passou.
- `openspec validate clarify-grouped-payment-reference --strict` — change válida.
- `git diff --check` — sem erros de whitespace; Git reportou avisos de conversão LF/CRLF em arquivos preexistentes da worktree.

## Limites

- Nenhuma migration de schema, alteração de UUID, regravação de snapshot ou operação em produção foi executada.
- A transformação da configuração ativa permanece só em prévia reversível. A aplicação remota depende da task 4.2 e de autorização operacional explícita.
