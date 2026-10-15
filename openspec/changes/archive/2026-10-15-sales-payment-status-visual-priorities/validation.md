# Validação

## Evidências automatizadas

- `backend`: `pytest tests/test_payment_status_visual_groups.py -q` — 2 passaram.
- `backend`: `pytest tests/test_derived_galleries.py -k admin_payment_dashboard -q` — 3 passaram, 87 foram ignorados pelo filtro.
- `backend`: `pytest tests/test_order_delivery.py -q` — 14 passaram.
- `backend`: `ruff check app/main.py tests/test_payment_status_visual_groups.py tests/test_derived_galleries.py` — sem achados.
- `frontend`: `npm test -- --run app/admin/payments/page.test.tsx` — 12 passaram.
- `frontend`: `npx eslint app/admin/payments/page.tsx app/admin/payments/page.test.tsx app/ui-kit.tsx` — sem achados.
- `frontend`: `npm run lint` — concluído, 0 erros e 25 avisos existentes em outras áreas do projeto.
- `frontend`: `npx tsc --noEmit` — concluído sem erros.
- `frontend`: `npm run build` — concluído; `/admin/payments` gerada.
- Raiz: `openspec validate sales-payment-status-visual-priorities --strict` — change válido.
- Raiz: `openspec validate --specs` — 11 specs passaram, incluindo a nova spec consolidada.
- Raiz: `git diff --check -- <arquivos desta mudança>` — sem erros de whitespace; Git emitiu apenas avisos de normalização LF/CRLF.

## Revisão manual

- A situação `confirmed_undelivered` é derivada de pagamento confirmado sem `delivery_album_url`; link presente mantém `confirmed`, e a contagem de receita confirmada inclui ambas as situações.
- Backend define prioridade, escolhe a situação financeira prioritária do cliente e pagina com prioridade, chegada e UUID; os pedidos permanecem individualmente ordenados e visíveis.
- Frontend não renderiza nem envia `delivery_status`; mantém estados/indicadores de mensagem consumidos em outros elementos. `No carrinho` aparece depois dos grupos financeiros.
- Opções, badges, cards e bordas compartilham tokens por situação; há valores de tema claro e escuro, rótulos textuais e teal próprio para `No carrinho`.
- O workspace já continha modificações locais amplas antes desta mudança. Foram preservadas; nenhuma limpeza, reset, staging, commit, migration ou deploy foi feita.

## Estado

Validação local e revisão humana aprovadas. A spec principal `openspec/specs/gallery-sales/payment-operations-dashboard/spec.md` foi criada e validada a partir da delta aprovada. Esta change será arquivada em `openspec/changes/archive/2026-10-15-sales-payment-status-visual-priorities/`.

## Revalidação na base `origin/main`

- `backend`: testes focados do dashboard — 3 passaram; `test_payment_status_visual_groups.py` — 2 passaram; entrega — 14 passaram; cartão, checkout e notificações — 38 passaram e 5 foram ignorados.
- `backend`: `ruff check app tests` — sem achados.
- `frontend`: `npm test` — 517 passaram em 60 arquivos; `npx tsc --noEmit` — sem erros; `npm run build` — concluído; `npm run lint` — 0 erros e 31 avisos preexistentes.
- `openspec validate --specs` — 21 specs passaram.
- `openspec validate --strict --all` — encontrou 33 falhas em changes ativos preexistentes fora desta change; a spec consolidada desta change é válida. O resultado integral será confirmado pelo check do PR.
