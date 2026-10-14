# Spec Delta

## ADDED Requirements

### Requirement: Busca de cliente por nome ou telefone em Vendas e pagamentos

A área Vendas e pagamentos SHALL manter um único filtro de cliente que localize registros por nome ou telefone cadastrado e ofereça sugestões de clientes correspondentes durante a digitação.

#### Scenario: Sugestões de nome

- **WHEN** o fotógrafo digita parte do nome de uma cliente no filtro existente
- **THEN** a área sugere nomes correspondentes e permite escolher uma cliente sem criar outro campo de busca

#### Scenario: Seleção exata ou busca livre

- **WHEN** o fotógrafo escolhe uma sugestão ou aplica texto parcial de nome/telefone
- **THEN** a área filtra seleções abertas e pedidos pela identidade escolhida ou pelo texto informado, respectivamente

#### Scenario: Paginação com busca

- **WHEN** a busca por cliente possui resultados em mais de uma página
- **THEN** carregar clientes adicionais preserva o mesmo critério de nome ou telefone

### Requirement: Filtros de vendas visíveis no topo durante a rolagem

A área Vendas e pagamentos SHALL posicionar o filtro existente antes dos resumos e listas operacionais e mantê-lo acessível abaixo da navegação administrativa durante a rolagem, sem cobrir conteúdo nem controles em telas pequenas.

#### Scenario: Consulta inicial

- **WHEN** o fotógrafo abre Vendas e pagamentos
- **THEN** encontra o filtro antes de Seleções em aberto, pedidos e demais cards operacionais

#### Scenario: Rolagem do painel

- **WHEN** o fotógrafo rola pelos cards e listas
- **THEN** o filtro permanece acessível no topo abaixo da navegação e não encobre os controles operacionais
