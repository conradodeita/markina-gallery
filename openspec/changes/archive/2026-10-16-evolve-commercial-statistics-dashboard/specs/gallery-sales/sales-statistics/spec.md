# Spec Delta

## Purpose

Definir um painel comercial e financeiro auditável com filtros coerentes, isolamento por fotógrafo, identificação de itens vendidos e exports calculados pela mesma fonte.

## ADDED Requirements

### Requirement: Estatísticas comerciais isoladas por fotógrafo

O sistema SHALL calcular cada resposta e filtro de Estatísticas no tenant resolvido da sessão administrativa no backend. IDs de tenant enviados pelo cliente MUST NOT determinar o escopo. Pedidos, itens, seleções, galerias, pastas e clientes SHALL pertencer ao mesmo tenant antes de entrarem em agregações ou exports.

#### Scenario: Fotógrafo consulta suas estatísticas

- **WHEN** um fotógrafo autenticado consulta o dashboard ou HTML
- **THEN** indicadores, opções de filtro, tabelas e relatório incluem apenas registros do tenant da sessão

#### Scenario: Tentativa de filtrar outro tenant

- **WHEN** uma requisição contém IDs de galeria, pasta ou cliente de outro tenant
- **THEN** o backend retorna resultado neutro sem expor registros, nomes, valores ou sua existência

### Requirement: Indicadores financeiros com denominadores explícitos

O sistema SHALL calcular receita efetiva, pedidos confirmados, itens vendidos e ticket médio com denominadores explícitos. Totais por item, pasta e galeria SHALL ser atribuídos sem duplicação. Uma divisão por zero SHALL produzir estado sem dados, não taxa inventada.

#### Scenario: Pedido com diversas fotografias

- **WHEN** um pedido confirmado possui várias linhas de item
- **THEN** a receita conta o pedido uma vez, a quantidade de fotos conta cada item e os totais de pastas somam os itens atribuídos a cada pasta

#### Scenario: Pedido corrigido ou pendente

- **WHEN** o pedido não está atualmente confirmado ou o pagamento do provedor está em hold
- **THEN** o pedido não compõe receita, ticket médio, fotos vendidas ou CSV de vendas

#### Scenario: Fórmulas financeiras

- **WHEN** a API calcula os indicadores do escopo filtrado
- **THEN** receita é a soma dos totais dos pedidos confirmados, pedidos é a contagem de UUIDs distintos, fotos vendidas é a contagem de itens confirmados e ticket médio é receita dividida por pedidos

### Requirement: Seleção sem compra distinta de abandono

O sistema SHALL distinguir seleção sem compra, pedido pendente, pagamento confirmado, cancelamento, finalização sem cobrança e abandono. Abandono SHALL exigir seleção persistida cujo prazo de seleção configurado para a galeria/cliente expirou e ausência de qualquer pedido associado. Seleções sem prazo vencido e pedidos existentes MUST NOT ser classificados como abandonados.

#### Scenario: Seleção recém-criada

- **WHEN** existem seleções sem pedido confirmado e sem evidência de expiração por inatividade
- **THEN** elas aparecem como seleções sem compra e não compõem valor ou contagem de abandono

#### Scenario: Pedido aguardando pagamento

- **WHEN** o pedido está pendente
- **THEN** permanece no grupo pendente e não é receita nem abandono

#### Scenario: Seleção expirada sem pedido

- **WHEN** há seleção persistida, o prazo da galeria/cliente venceu e não existe pedido associado
- **THEN** a oportunidade é contada uma vez como abandonada e suas fotos são identificadas

#### Scenario: Seleção convertida, cancelada ou sem cobrança

- **WHEN** existe pedido confirmado, cancelado, pendente ou finalizado sem cobrança para a seleção
- **THEN** ela permanece no estado comercial correspondente e não é contada como abandono

#### Scenario: Preço potencial sem snapshot

- **WHEN** uma seleção abandonada não tem preço congelado persistido
- **THEN** a interface informa valor potencial indisponível e não usa o preço atual da galeria


### Requirement: Conversão por seleção resolvida

O sistema SHALL contar cada fotografia uma vez por cliente/galeria. O denominador SHALL incluir fotografias selecionadas compradas ou expiradas sem pedido; seleções não expiradas e seleções com outro estado de pedido ficam fora. Com denominador zero, a taxa SHALL ser indisponível.

#### Scenario: Denominador da conversão

- **WHEN** a conversão é exibida
- **THEN** o relatório informa o número comprado e o denominador de seleções resolvidas, sem contar pedidos pendentes, cancelados ou sem cobrança

#### Scenario: Recorte sem vínculo com seleção

- **WHEN** pasta, pagamento ou status do pedido não pode ser relacionado com segurança às seleções persistidas
- **THEN** os indicadores de seleção e abandono são apresentados como indisponíveis, sem substituir ausência de vínculo por zero

### Requirement: Detalhamento de venda e pagamento

O sistema SHALL permitir consultar dados comerciais congelados do cliente, pedido, confirmação, galeria, pasta, fotografia, quantidade, valores, forma de pagamento, destino mapeado e status atual. Fotos e pastas SHALL usar snapshots quando a mídia operacional não existir.

#### Scenario: Pedido com fotos de pastas diferentes

- **WHEN** um pedido confirmado contém itens de pastas diferentes
- **THEN** cada foto e seu valor aparecem uma vez na pasta congelada no item, e a soma das pastas corresponde à soma dos itens

#### Scenario: Foto removida após compra

- **WHEN** a mídia de um item comprado não existe mais
- **THEN** o relatório mantém identificação, nome, pasta e preço congelados do item sem URL ou ID nulo

#### Scenario: Forma de pagamento e destino

- **WHEN** o item pertence a pedido confirmado por PIX ou crédito
- **THEN** o relatório preserva a forma registrada e mapeia o destino para Nubank ou InfinityPay, respectivamente; forma desconhecida fica sem destino inventado

### Requirement: Reconciliação financeira visível

O sistema SHALL comparar a soma dos preços unitários dos itens de cada pedido com o total persistido do pedido, sinalizar diferenças com ID do pedido, total do pedido, total calculado e diferença, e MUST NOT corrigir valores silenciosamente. Os totais exportados SHALL corresponder às linhas de itens incluídas no mesmo escopo. Ajustes ou reembolsos sem evento/campo persistido SHALL ser identificados como limitação e não presumidos.

#### Scenario: Total dos itens diverge do pedido

- **WHEN** a soma dos itens difere do total registrado
- **THEN** o pedido é listado na conciliação com os dois valores e a diferença, sem alterar a receita registrada

#### Scenario: Totais por pasta e galeria

- **WHEN** o fotógrafo filtra ou agrega por pasta ou galeria
- **THEN** os subtotais correspondem à soma dos itens efetivamente atribuídos e cada item aparece em uma única pasta

### Requirement: HTML comercial autônomo

O sistema SHALL oferecer ao fotógrafo um HTML responsivo, autocontido e filtrado usando a mesma consulta e regras do dashboard. O arquivo MUST abrir sem sessão, API, scripts externos, tokens, credenciais ou URLs de mídia privada e SHALL conter vendas detalhadas, indicadores, filtros aplicáveis ao conteúdo exportado, totais por galeria/pasta e seção separada para seleções sem compra.

#### Scenario: Consulta offline

- **WHEN** o fotógrafo abre o HTML salvo sem conectividade ou sessão
- **THEN** dados e estilos já exportados permanecem disponíveis localmente

### Requirement: CSV de vendas exclusivo do proprietário

O sistema SHALL autorizar o CSV somente para a conta do proprietário do Monitor identificada pelo UUID persistido em `platform_owner`, com sessão, vínculo e tenant ativos. O endpoint MUST NOT usar o e-mail como regra de acesso, SHALL negar outras contas antes de consultar dados e SHALL revalidar a propriedade após a consulta. Os dados do CSV permanecem limitados ao tenant autorizado pela sessão. A implementação MUST NOT modificar o Monitor.

#### Scenario: Conta proprietária atual

- **WHEN** a conta proprietária validada solicita CSV com filtros
- **THEN** o backend gera somente os dados daquele tenant e usa os filtros aplicados

#### Scenario: Troca do e-mail do proprietário

- **WHEN** a mesma conta proprietária troca o e-mail verificado
- **THEN** o acesso permanece pelo UUID persistido em `platform_owner`

#### Scenario: Outra conta ou proprietário ausente

- **WHEN** outro fotógrafo tenta acessar o endpoint, ou o registro de proprietário está ausente/inválido
- **THEN** o backend responde sem dados antes de consultar o relatório, mesmo que existam permissões/grants do Monitor

### Requirement: CSV estruturado por item

O sistema SHALL gerar CSV UTF-8 com delimitador `;`, decimal com ponto, datas `AAAA-MM-DD`, valores monetários exatos, escaping correto e cabeçalhos fixos documentados. Cada linha SHALL representar um item e MUST NOT repetir o total do pedido.

#### Scenario: Pedido com vários itens

- **WHEN** um pedido confirmado possui mais de um item
- **THEN** cada linha repete o mesmo pedido_id, contém seu próprio total_item e não replica o total do pedido

#### Scenario: CSV seguro em resposta direta

- **WHEN** o proprietário baixa o CSV
- **THEN** ele é entregue sem arquivo público persistente, com `private, no-store` e proteção contra interpretação de conteúdo ativo

#### Scenario: Cabeçalhos comerciais

- **WHEN** o CSV inclui linhas de itens
- **THEN** cada linha contém `pedido_id`, `cliente_nome`, `cliente_telefone`, `data`, `galeria_id`, `galeria_nome`, `pasta_id`, `pasta_nome`, `item_id`, `fotografia_id`, `fotografia_nome`, `quantidade`, `valor_unitario`, `total_item`, `forma_pagamento`, `conta_destino` e `categoria`, com categoria `Fotografia`
