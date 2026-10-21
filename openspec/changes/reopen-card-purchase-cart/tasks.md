# Tasks

## 1. Serviço de recuperação e transação

- [x] 1.1 Implementar prévia/reabertura por compra com ownership, confirmação explícita, fingerprint, seleção integral, histórico e idempotência; executar regressões sintéticas de PIX/cartão disponíveis, fotos novas, simulação/rollback, estado confirmado/falha clara, snapshot e repetição após nova compra. Registrar evidências e revisão proporcional de reutilização.
- [x] 1.2 Proteger a emissão contra resposta tardia e testar reabertura/confirmador/emissão concorrentes em PostgreSQL isolado, comprovando ausência de regressão de estado e de restauração duplicada.

## 2. API e card da cliente

- [x] 2.1 Expor prévia/confirmação administrativas, capacidade/revisão/indicador na projeção e revisão de recuperação da própria cliente no carrinho; testar autenticação, isolamento A/B, inputs, conflito, fotos canônicas e preservação de decisões PIX/receitas/entregas.
- [x] 2.2 Implementar Reabrir carrinho no card da cliente por compra e retomada no carrinho com chave nova após reabertura validada, sem selecionar novamente; executar testes de componente para prévia/confirmar/cancelar, falha, duplo clique, estados confirmados sem ação e idempotência da emissão incerta, mantendo filtros/fotos/paginação.
- [x] 2.3 Identificar reabertura auditada no histórico da cliente com acesso ao carrinho e omitir rascunho PIX não comunicado do painel financeiro, preservando seleção, comunicação/confirmados e registros. Reproduzir o cenário e executar regressões API/UI.
- [x] 2.4 Aplicar a mesma visibilidade comercial às listas de pedidos da galeria e ao contador de pedidos no diretório do fotógrafo, sem alterar inventário/proteção de exclusão. Comprovar que o rascunho não reaparece como pedido duplicado nas demais telas e que pagamentos comunicados continuam visíveis.

## 3. Integração e entrega

- [x] 3.1 Executar gates locais pertinentes (backend focado/amplo, PostgreSQL, Ruff, frontend testes/lint/TypeScript/build, OpenSpec), revisar diff por regressões/duplicação e preparar PR draft empilhado sobre #263 com evidências, plano mínimo de publicação/rollback e bloqueios reais. Não modificar #261/#262/#264, publicar, mesclar ou alterar compras reais.
- [x] 3.2 Corrigir a conversão do UUID recebido por HTTP na consulta de teste apontada pelo CI 39660195152, reproduzir a falha e repetir os testes da API em SQLite, preservando todas as expectativas de produto. Executar Ruff/OpenSpec e revisar o diff antes de enviar a correção ao mesmo PR draft; o novo CI completo permanece gate externo.

## Workflow follow-up

- Publicação de API/web exige autorização operacional própria; a autorização de implementar a ação manual não autoriza deploy ou novos pagamentos reais.
- CI completo do head final do PR #265 é gate externo obrigatório antes de declarar aptidão para publicação; acompanhar o resultado no próprio PR/run. O resultado parcial/antigo não vale como CI final, mesmo com tasks locais concluídas.
- Após o push da correção de 39660195152, o proprietário acompanhará o novo CI e trará o resultado; o executor deve parar o acompanhamento conforme instrução expressa de 21/10/2026.
- Sincronizar/arquivar somente após revisão humana. Gates de webhook/reconciliação universal continuam como seguimento independente.
