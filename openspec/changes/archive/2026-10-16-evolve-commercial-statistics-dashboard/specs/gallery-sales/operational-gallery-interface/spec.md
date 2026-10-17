# Spec Delta

## Purpose

Adicionar uma experiência responsiva de gestão comercial às Estatísticas, preservando os fluxos e a autorização administrativa existentes.

## MODIFIED Requirements

### Requirement: Estados operacionais claros

O sistema SHALL apresentar estados de carregamento, vazio, erro, preparação, progresso, sucesso, bloqueio e expiração nas telas administrativas e da cliente, com linguagem compreensível e ação de recuperação quando aplicável. A página Estatísticas SHALL apresentar estados distintos para ausência de vendas, seleções sem compra, dados indisponíveis e falha de consulta, sem substituir falhas ou dados não instrumentados por zero.

#### Scenario: Falha ao consultar estatísticas

- **WHEN** a API de Estatísticas falha
- **THEN** a página informa erro recuperável, preserva filtros e não exibe receita zero como se fosse resultado real

#### Scenario: Importação em processamento

- **WHEN** um JPEG foi aceito e seus derivados ainda estão sendo preparados
- **THEN** o fotógrafo vê o estado pendente sem receber URL do original

#### Scenario: Liberação concluída

- **WHEN** o fotógrafo conclui a liberação de uma pasta
- **THEN** a interface confirma o público efetivo retornado pelo backend e as clientes alcançadas, sem sugerir atualização de galerias derivadas

#### Scenario: Galeria sem prazo de seleção configurado

- **WHEN** a galeria/cliente não tem prazo de seleção persistido ou ele ainda não expirou
- **THEN** suas seleções não são classificadas como abandonadas e nenhum prazo ou valor potencial é inventado

### Requirement: Interface orientada pelo backend

O sistema SHALL obter dados, permissões, disponibilidade e resultados exclusivamente de APIs autenticadas do backend. Estatísticas SHALL oferecer filtros combináveis por período, evento, galeria, pasta, cliente, meio de pagamento e status do pedido; tabelas e indicadores SHALL refletir o mesmo escopo. Valores consolidados SHALL permitir abrir os registros detalhados correspondentes. A interface SHALL NOT conceder acesso ao CSV por ocultação de botão apenas.

#### Scenario: Filtros combinados

- **WHEN** o fotógrafo combina período, galeria, pasta, cliente ou forma de pagamento
- **THEN** indicadores, detalhamento HTML e subtotais refletem exatamente o mesmo conjunto autorizado de itens/pedidos

#### Scenario: Acesso a exportação CSV

- **WHEN** a interface apresenta a ação de CSV
- **THEN** o backend ainda revalida a autorização do proprietário para a URL direta e a ação

#### Scenario: Estado administrativo

- **WHEN** o fotógrafo abre ou altera uma tela operacional
- **THEN** a interface consulta o backend e apresenta o estado retornado, sem criar autorização ou registros simulados no browser

#### Scenario: Consulta por responsável

- **WHEN** o fotógrafo busca por nome ou telefone na ficha de uma galeria-fonte
- **THEN** o sistema retorna apenas os vínculos e estados autorizados da consulta e permite abrir a ficha individual da seleção
