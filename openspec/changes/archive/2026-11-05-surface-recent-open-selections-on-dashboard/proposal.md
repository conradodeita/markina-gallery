# Proposal

## Why

O card “Acesso recente” mostra galerias, mas não ajuda o fotógrafo a identificar clientes que já selecionaram fotos e ainda estão em uma seleção ativa. O fotógrafo precisa abrir Vendas e pagamentos e localizar manualmente esse carrinho para acompanhar a oportunidade.

## What Changes

- Acrescentar ao card atual uma lista curta de clientes com seleções atuais, usando as linhas `PhotoSelection` já existentes e escopo do tenant autenticado.
- Apresentar cliente, galeria, quantidade de fotos e o horário exato em que a seleção atual começou; ordenar pelos grupos cuja seleção recebeu atividade mais recente.
- Persistir esse horário em uma coluna opcional do estado já existente da cliente/galeria, reiniciando quando um novo carrinho começar.
- Manter a lista e os atalhos de galerias recentes existentes.
- Permitir abrir Vendas e pagamentos já filtrado para o cliente e a Galeria pública correspondentes, levando o fotógrafo ao cartão de seleção atual ou ao cartão financeiro do cliente quando o estado tiver mudado.
- Manter as regras de pedidos, pagamentos, prazos e seleção existentes, sem criar histórico paralelo nem nova tabela.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: a Visão geral apresenta clientes com seleção atual, respeitando o tenant e mantendo os atalhos de galerias.
- `gallery-sales/payment-operations-dashboard`: links diretos iniciam os filtros de cliente/galeria e focam o cartão correspondente, incluindo seleções abertas.

## Impact

- Backend: coluna aditiva no estado da cliente/galeria e projeção compacta em `/admin/validation-summary`, limitada aos registros do tenant autenticado.
- Frontend: lista no card “Acesso recente”; leitura dos parâmetros de cliente/galeria em Vendas e pagamentos e foco no cartão correspondente.
- Sem nova tabela, dependência, integração externa ou mudança nas regras de pagamento. A migration aditiva cria somente o campo de início atual; não preencherá horários históricos que não possam ser comprovados.

## Limite do histórico

A lista representa seleções que ainda têm registros atuais em `PhotoSelection`. Ela não pretende mostrar uma seleção depois que as fotos forem removidas ou o checkout for congelado/finalizado. Esse limite permite reaproveitar o estado comercial atual, em vez de alterar o marco de notificação `first_selection`, que é único por cliente/galeria e possui linhas de baseline para vínculos anteriores. Carrinhos já ativos antes desta mudança podem continuar visíveis sem horário exato e SHALL mostrar “Horário não registrado”; não haverá tentativa de reconstrução. O início de cada nova seleção será registrado daqui em diante.
