## 1. Persistência comercial e cálculo

- [ ] 1.1 Criar migration aditiva para regras de preço, snapshots comerciais e instruções PIX estruturadas, verificando upgrade e downgrade em banco sintético.
- [ ] 1.2 Implementar validação e cálculo servidor-side de faixas contíguas em centavos inteiros, incluindo alerta de salto comercial, e verificar testes unitários de limites e totais.
- [ ] 1.3 Implementar criação transacional de pedido pendente a partir da seleção autorizada, congelando itens, preços, regra e texto comercial; verificar idempotência e preservação de pedidos anteriores.

## 2. APIs autorizadas

- [ ] 2.1 Expor APIs da cliente para consultar carrinho, alterar seleção elegível, simular total e finalizar checkout, verificando isolamento entre galerias e responsáveis.
- [ ] 2.2 Expor APIs administrativas para configurar regras de preço e instruções PIX controladas, verificando validação de lacunas, sobreposição e ausência de segredos em respostas.
- [ ] 2.3 Expor consulta privada do pedido pendente e instruções PIX somente à cliente proprietária, verificando que o acesso de terceiros recebe resposta neutra.

## 3. Interfaces de cliente e fotógrafo

- [ ] 3.1 Implementar carrinho e checkout mobile-first da cliente, com quantidade, faixa aplicada, estimativa, remoção e estado pendente de confirmação, verificando estados vazio, erro e acessibilidade.
- [ ] 3.2 Implementar painel administrativo de regras por faixa, simulador e instruções PIX estruturadas, verificando alerta de salto comercial e controles sem CSS ou campos livres inseguros.
- [ ] 3.3 Implementar visão administrativa de pedidos pendentes e confirmados sem alterar a decisão financeira, verificando que o pedido congelado é exibido com seus snapshots.

## 4. Qualidade e integração

- [ ] 4.1 Cobrir autorização, prazo, prevenção de recompra própria, cálculo monetário, imutabilidade e concorrência de checkout com testes backend relevantes.
- [ ] 4.2 Cobrir carrinho, checkout, regras por faixa e estados PIX com testes frontend relevantes.
- [ ] 4.3 Executar migrations, testes, lint, typecheck, build e validação OpenSpec estrita; validar homologação somente com dados sintéticos e sem ativar provedor de pagamento.
- [ ] 4.4 Atualizar documentação operacional de configuração de PIX manual, rollback e ligação com a confirmação manual, verificando que `.env`, credenciais e dados bancários não são versionados.
