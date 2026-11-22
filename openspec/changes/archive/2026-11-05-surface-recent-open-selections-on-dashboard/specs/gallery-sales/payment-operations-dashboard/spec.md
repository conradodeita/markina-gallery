## ADDED Requirements

### Requirement: Atalho contextual para seleção atual
Vendas e pagamentos SHALL aceitar um link administrativo com os identificadores de cliente e Galeria pública. Esse link SHALL inicializar os filtros exatos para esses registros e usar a situação financeira `Todas`, de modo que seleções atuais continuem visíveis. A abertura direta SHALL preservar autenticação, autorização e isolamento do tenant; a rota SHALL continuar aplicando os mesmos filtros no backend.

#### Scenario: Abrir uma seleção pelo painel
- **WHEN** o fotógrafo autenticado ativa o cliente de uma seleção atual na Visão geral
- **THEN** Vendas e pagamentos abre filtrado pela cliente e pela Galeria pública correspondentes e posiciona a tela no cartão “No carrinho” daquela seleção

#### Scenario: Seleção muda antes do clique
- **WHEN** o estado muda entre carregar a Visão geral e abrir o atalho, mas ainda há pedido do cliente no filtro
- **THEN** a página posiciona o cartão financeiro do mesmo cliente como alternativa, sem mostrar registros de outra conta

#### Scenario: Nenhum registro restante
- **WHEN** não há seleção atual nem pedido correspondente no momento da consulta
- **THEN** o filtro permanece limitado à cliente e galeria informadas e apresenta o estado vazio existente, sem simular atividade

#### Scenario: Abertura normal de Vendas e pagamentos
- **WHEN** o fotógrafo abre a rota sem o atalho contextual
- **THEN** o painel mantém seu filtro inicial de pendências prioritárias e seu comportamento atual
