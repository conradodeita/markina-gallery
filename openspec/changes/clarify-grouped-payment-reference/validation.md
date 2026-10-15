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

## Revalidação após integração com `develop` — 2026-10-15

- Merge do `origin/develop` atualizado preservou o escopo multi-tenant da configuração/eventos e a ação existente de download de fotos compradas; os sete conflitos foram resolvidos no checkout isolado do PR, sem tocar a worktree principal.
- `python -m pytest -q tests/test_payment_templates.py tests/test_notification_settings.py tests/test_notification_payments.py tests/test_unified_checkout.py` — 35 passed, 5 skipped.
- `npm test -- --run app/admin/payments/payment-actions.test.tsx app/admin/payments/page.test.tsx app/admin/notifications/page.test.tsx` — 25 passed.
- `npx tsc --noEmit` e ESLint nos arquivos administrativos tocados — passaram.
- `openspec validate clarify-grouped-payment-reference --strict` — change válida.
- `git diff --check` — sem erros de whitespace.
- `npm ci` reportou 11 alertas no audit das dependências resolvidas (10 altos, 1 crítico); nenhuma atualização de dependências foi incluída nesta change.

## Limites

- Nenhuma migration de schema, alteração de UUID, regravação de snapshot ou operação em produção foi executada.
- A transformação da configuração ativa permanece só em prévia reversível. A aplicação remota depende da task 4.2 e de autorização operacional explícita.

## Inventário remoto somente leitura — 2026-10-15

Inspecionada a tela autenticada de notificações em `https://markina.pickyourpic.com.br/admin/notifications`. Os canais Push e WhatsApp estavam habilitados para os três eventos abaixo. Nenhum campo foi editado ou salvo. A prévia padrão da tela usa dados fictícios (`Cliente`, `Galeria`, `1234abcd`) e não representa, por si só, o texto entregue a um grupo.

| Evento/campo | Texto ativo observado | Prévia local da transformação | Resultado |
| --- | --- | --- | --- |
| `payment_reported` — título Push | `Pagamento informado` | igual | sem alteração |
| `payment_reported` — corpo Push e WhatsApp | `{{cliente}} informou pagamento do pedido {{pedido}}.` | `{{cliente}} informou pagamento {{contexto_pagamento}}.` | frase reconhecida; código e texto externo preservados |
| `payment_confirmed` — título Push | `Pagamento confirmado` | igual | sem alteração |
| `payment_confirmed` — corpo Push | `Confirmamos o pagamento do seu pedido.` | igual | sem alteração |
| `payment_confirmed` — corpo WhatsApp | `Olá {{cliente}}, essa mensagem é automática, confirmamos o pagamento do pedido {{pedido}} da galeria {{galeria}}. Suas fotos seguirão para edição.` | `Olá {{cliente}}, essa mensagem é automática, confirmamos o pagamento {{contexto_pagamento}}. Suas fotos seguirão para edição.` | frase reconhecida; código e restante do texto preservados |
| `payment_refused` — título Push | `Pagamento não localizado` | igual | sem alteração |
| `payment_refused` — corpo Push | `Não localizamos seu pagamento. Confira seu pedido.` | igual | sem alteração |
| `payment_refused` — corpo WhatsApp | `Olá {{cliente}}, não localizamos o pagamento do pedido {{pedido}} da galeria {{galeria}}. Revise os dados antes de comunicar novamente.` | `Olá {{cliente}}, não localizamos o pagamento {{contexto_pagamento}}. Revise os dados antes de comunicar novamente.` | frase reconhecida; código e restante do texto preservados |

Os corpos Push e WhatsApp observados para `payment_reported` eram iguais e ambos estavam habilitados. A prévia acima foi calculada pelo código local da change, não pela instância remota: o endpoint de prévia ainda depende da publicação do código e nenhum endpoint remoto foi chamado. A interface não expôs versões internas nem uma exportação recuperável das configurações; portanto esse inventário visual não é backup operacional suficiente.

### Plano operacional pendente

1. Obter autorização explícita para publicar o código da change; sem ele, a variável `{{contexto_pagamento}}` pode não ser renderizada pela aplicação atual.
2. Antes de alterar templates ativos, obter autorização operacional específica e gerar backup recuperável das três configurações efetivas (corpos Push/WhatsApp, títulos, canais habilitados e versões), além de registrar a versão do serviço e conferir os snapshots/outbox existentes sem modificá-los.
3. Após a publicação autorizada, chamar somente a prévia autenticada, comparar o `before` com este inventário e confirmar que apenas as frases reconhecidas mudam. Divergência de template, canal ou versão interrompe a aplicação até nova revisão.
4. Só aplicar a transformação após aprovação explícita do diff e do backup. Conferir as configurações futuras e demonstrar que notificações/snapshots históricos não foram reescritos. Ter procedimento de restauração dos campos de configuração usando o backup.

Até a aprovação e execução desses passos, task 4.2 permanece pendente. O inventário não autoriza publicação, escrita remota nem envio de mensagens.
