# Tasks

## 1. Serviço de recuperação e transação

- [x] 1.1 Implementar prévia/reabertura por compra com ownership, confirmação explícita, fingerprint, seleção integral, histórico e idempotência; executar regressões sintéticas de PIX/cartão disponíveis, fotos novas, simulação/rollback, estado confirmado/falha clara, snapshot e repetição após nova compra. Registrar evidências e revisão proporcional de reutilização.
- [x] 1.2 Proteger a emissão contra resposta tardia e testar reabertura/confirmador/emissão concorrentes em PostgreSQL isolado, comprovando ausência de regressão de estado e de restauração duplicada.

## 2. API e card da cliente

- [x] 2.1 Expor prévia/confirmação administrativas, capacidade/revisão/indicador na projeção e revisão de recuperação da própria cliente no carrinho; testar autenticação, isolamento A/B, inputs, conflito, fotos canônicas e preservação de decisões PIX/receitas/entregas.
- [x] 2.2 Implementar Reabrir carrinho no card da cliente por compra e retomada no carrinho com chave nova após reabertura validada, sem selecionar novamente; executar testes de componente para prévia/confirmar/cancelar, falha, duplo clique, estados confirmados sem ação e idempotência da emissão incerta, mantendo filtros/fotos/paginação.

## 3. Integração e entrega

- [ ] 3.1 Executar gates pertinentes (backend focado/amplo, PostgreSQL, Ruff, frontend testes/lint/TypeScript/build, OpenSpec), revisar diff por regressões/duplicação e preparar PR draft empilhado sobre #263 com evidências, plano mínimo de publicação/rollback e bloqueios reais. Não modificar #261/#262/#264, publicar, mesclar ou alterar compras reais.

## Workflow follow-up

- Publicação de API/web exige autorização operacional própria; a autorização de implementar a ação manual não autoriza deploy ou novos pagamentos reais.
- Sincronizar/arquivar somente após revisão humana. Gates de webhook/reconciliação universal continuam como seguimento independente.
