# Spec Delta

## ADDED Requirements

### Requirement: Apresentação responsiva da Visão Geral do fotógrafo

A Visão Geral SHALL reunir navegação, busca de galerias e ações de sessão no mesmo enquadramento visual que os indicadores, galerias e ações reais da conta. No desktop, a navegação SHALL ficar na barra lateral da Visão Geral. No celular, a navegação SHALL ser recolhível e as seções empilhadas. A carteira SHALL distinguir carregamento, saldo disponível, ausência de movimentações e erro. A tela MUST preservar navegação por teclado, foco visível e preferência de movimento reduzido.

#### Scenario: Fotógrafo consulta o painel

- **WHEN** a resposta autenticada da Visão Geral está disponível
- **THEN** a tela organiza os cinco indicadores existentes, a prática de publicação, galerias e seleções recentes, preservando seus atalhos e usando estado sem capa quando a resposta não fornece imagens

#### Scenario: Fotógrafo usa o painel em uma janela estreita

- **WHEN** a Visão Geral é exibida em largura de celular
- **THEN** a navegação recolhe, os indicadores usam uma coluna e as ações permanecem acessíveis sem rolagem horizontal

#### Scenario: Fotógrafo usa os atalhos da Visão Geral

- **WHEN** o fotógrafo acessa a busca, aparência ou conta pela Visão Geral
- **THEN** a busca leva ao filtro existente de Galerias, e as ações de tema e sessão usam seus controles e permissões existentes

#### Scenario: Consulta da carteira independente

- **WHEN** a carteira aguarda resposta, possui saldo sem movimentações ou falha ao carregar
- **THEN** o painel apresenta o estado correspondente e mantém disponíveis os indicadores e atalhos operacionais já carregados

### Requirement: Apresentação dos catálogos administrativos

Galerias e Clientes SHALL reutilizar a navegação responsiva do painel do fotógrafo e os endpoints autenticados de cada catálogo. A UI MUST apresentar carregamento, erro e resultados vazios, refletir apenas os registros autorizados e preservar as ações e rotas existentes.

#### Scenario: Fotógrafo consulta Galerias

- **WHEN** o fotógrafo busca ou alterna a apresentação do catálogo
- **THEN** os cartões usam as galerias públicas retornadas, exibem capa somente quando fornecida e mantêm criação e abertura dos detalhes autorizados

#### Scenario: Fotógrafo consulta Clientes

- **WHEN** o fotógrafo busca, carrega mais clientes ou abre uma ação de cadastro ou edição
- **THEN** o diretório apresenta somente registros retornados da conta, mantém a paginação existente e delega as mudanças aos controles autorizados existentes

#### Scenario: Fotógrafo edita uma cliente em janela de altura limitada

- **WHEN** o editor de cliente está aberto e seu conteúdo cresce além do espaço disponível
- **THEN** o editor permite alcançar todas as ações por rolagem interna e preserva a posição da página ao fechar

### Requirement: Apresentação do painel de Vendas e pagamentos

Vendas e pagamentos SHALL reutilizar a estrutura visual responsiva do painel do fotógrafo e os contratos financeiros existentes.

#### Scenario: Fotógrafo consulta pedidos e utiliza ações financeiras

- **WHEN** o fotógrafo acessa a consulta, exporta um resultado ou abre um pedido
- **THEN** a UI exibe valores do filtro real, preserva busca e paginação, e delega decisões, notificações e entregas às permissões e aos controles existentes
