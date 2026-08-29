## 1. Persistência comercial e cálculo

- [x] 1.1 Criar migration aditiva para regras de preço, snapshots comerciais e instruções PIX estruturadas, verificando upgrade e downgrade em banco sintético. (`alembic upgrade 20260828_0012` e `downgrade 20260828_0010` em SQLite sintético: aprovados em 2026-08-29)
- [x] 1.2 Implementar validação e cálculo servidor-side de faixas contíguas em centavos inteiros, incluindo alerta de salto comercial, e verificar testes unitários de limites e totais. (`PYTHONPATH=/app pytest tests/test_pricing.py -q`: 8 aprovados no container em 2026-08-28)
- [x] 1.3 Implementar criação transacional de pedido pendente a partir da seleção autorizada, congelando itens, preços, regra e texto comercial; verificar idempotência e preservação de pedidos anteriores. (`test_pending_checkout_freezes_prices_pix_and_selection`: aprovado em 2026-08-29)

## 2. APIs autorizadas

- [x] 2.1 Expor APIs da cliente para consultar carrinho, alterar seleção elegível, simular total e finalizar checkout, verificando isolamento entre galerias e responsáveis. (`test_client_cart_and_checkout_are_private`: aprovado em 2026-08-29)
- [x] 2.2 Expor APIs administrativas para configurar regras de preço e instruções PIX controladas, verificando validação de lacunas, sobreposição e ausência de segredos em respostas. (`test_admin_pricing_requires_contiguous_tiers_and_returns_jump_warning`: aprovado em 2026-08-29)
- [x] 2.3 Expor consulta privada do pedido pendente e instruções PIX somente à cliente proprietária, verificando que o acesso de terceiros recebe resposta neutra. (`test_pending_order_is_private_and_preserves_pix_snapshot`: aprovado em 2026-08-29)

## 3. Interfaces de cliente e fotógrafo

- [x] 3.1 Implementar carrinho e checkout mobile-first da cliente, com quantidade, faixa aplicada, estimativa, remoção e estado pendente de confirmação, verificando estados vazio, erro e acessibilidade. (`gallery.test.tsx`: 6 aprovados em 2026-08-29)
- [x] 3.2 Implementar painel administrativo de regras por faixa, simulador e instruções PIX estruturadas, verificando alerta de salto comercial e controles sem CSS ou campos livres inseguros. (`pricing.test.tsx`: 2 aprovados em 2026-08-29)
- [x] 3.3 Implementar visão administrativa de pedidos pendentes e confirmados sem alterar a decisão financeira, verificando que o pedido congelado é exibido com seus snapshots. (`orders.test.tsx` e `test_admin_sees_pending_order_snapshots_without_confirming_it`: aprovados em 2026-08-29)

## 4. Qualidade e integração

- [x] 4.1 Cobrir autorização, prazo, prevenção de recompra própria, cálculo monetário, imutabilidade e concorrência de checkout com testes backend relevantes. (`test_pricing.py`, testes focados de checkout, prazo, autorização, imutabilidade e constraint de idempotência: aprovados em SQLite sintético em 2026-08-29)
- [x] 4.2 Cobrir carrinho, checkout, regras por faixa e estados PIX com testes frontend relevantes. (`gallery.test.tsx`, `pricing.test.tsx`, `orders.test.tsx`: 9 aprovados em 2026-08-29)
- [ ] 4.3 Executar migrations, testes, lint, typecheck, build e validação OpenSpec estrita; validar homologação somente com dados sintéticos e sem ativar provedor de pagamento. **Bloqueio:** as validações locais aplicáveis passaram em 2026-08-29; a validação sintética em homologação depende de integração humana da branch/PR em `develop` e da aprovação do Environment `homolog`, que este executor não pode executar autonomamente.
- [x] 4.4 Atualizar documentação operacional de configuração de PIX manual, rollback e ligação com a confirmação manual, verificando que `.env`, credenciais e dados bancários não são versionados. (`docs/OPERACAO-PIX-MANUAL.md` revisado em 2026-08-29)
