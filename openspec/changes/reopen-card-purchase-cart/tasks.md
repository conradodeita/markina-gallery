# Tasks

## 1. Serviço de recuperação e transação

- [x] 1.1 Implementar prévia/reabertura por compra com ownership, confirmação explícita, fingerprint, seleção integral, histórico e idempotência; executar regressões sintéticas de PIX/cartão disponíveis, fotos novas, simulação/rollback, estado confirmado/falha clara, snapshot e repetição após nova compra. Registrar evidências e revisão proporcional de reutilização.
- [x] 1.2 Proteger a emissão contra resposta tardia e testar reabertura/confirmador/emissão concorrentes em PostgreSQL isolado, comprovando ausência de regressão de estado e de restauração duplicada.

## 2. API e card da cliente

- [ ] 2.1 Expor prévia/confirmação administrativas e capacidade/revisão/indicador na projeção; testar autenticação, isolamento A/B, inputs, conflito e preservação de decisões PIX/receitas/entregas.
- [ ] 2.2 Implementar Reabrir carrinho no card da cliente por compra, com prévia/confirmar/cancelar, motivo, meios disponíveis e estado após sucesso; executar testes de componente para confirmação, falha, duplo clique e compras confirmadas sem ação, mantendo filtros/fotos/paginação.

## 3. Integração e entrega

- [ ] 3.1 Executar gates pertinentes (backend focado/amplo, PostgreSQL, Ruff, frontend testes/lint/TypeScript/build, OpenSpec), revisar diff por regressões/duplicação e preparar PR draft empilhado sobre #263 com evidências, plano mínimo de publicação/rollback e bloqueios reais. Não modificar #261/#262/#264, publicar, mesclar ou alterar compras reais.

## Workflow follow-up

- Publicação de API/web exige autorização operacional própria; a autorização de implementar a ação manual não autoriza deploy ou novos pagamentos reais.
- Sincronizar/arquivar somente após revisão humana. Gates de webhook/reconciliação universal continuam como seguimento independente.
