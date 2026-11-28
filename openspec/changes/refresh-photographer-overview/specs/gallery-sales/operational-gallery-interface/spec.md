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

### Requirement: Apresentação do formulário Nova galeria

O formulário inicial SHALL reutilizar a estrutura responsiva do fotógrafo e o endpoint autenticado de criação de galeria.

#### Scenario: Fotógrafo cria uma galeria

- **WHEN** o fotógrafo envia o título e os campos opcionais válidos
- **THEN** a UI envia uma solicitação de criação, apresenta o andamento e abre Ajustes a partir do identificador retornado

#### Scenario: Criação é rejeitada ou fica sem confirmação

- **WHEN** a solicitação falha ou o identificador da nova galeria não pode ser confirmado
- **THEN** a UI mantém os valores digitados e apresenta o estado correspondente, orientando a conferência do catálogo em caso de resultado incerto

### Requirement: Apresentação da configuração de notificações

Notificações SHALL usar o painel responsivo do fotógrafo e representar os eventos e as permissões fornecidos pela API autenticada.

#### Scenario: Fotógrafo filtra, edita ou acessa diretamente um evento

- **WHEN** alterna o destinatário, modifica um texto ou abre um evento por link direto
- **THEN** o painel preserva o rascunho, apresenta prévia local e usa a configuração e versão existentes ao salvar

#### Scenario: Canal de WhatsApp indisponível

- **WHEN** a API indica que o canal de WhatsApp não está disponível para edição
- **THEN** a UI mantém os controles de WhatsApp bloqueados e permite configurar push independentemente

### Requirement: Apresentação das tabelas de preço progressivo

Tabelas de preço progressivo SHALL usar a estrutura visual responsiva do fotógrafo e preservar as operações administrativas existentes.

#### Scenario: Fotógrafo consulta ou modifica tabelas

- **WHEN** consulta o catálogo, configura as faixas de uma tabela ou muda sua disponibilidade
- **THEN** a interface mostra os dados autorizados, usa valores em centavos nas operações, mantém a confirmação de desativação e apresenta a versão e os estados retornados

### Requirement: Apresentação das configurações do fotógrafo

Configurações SHALL organizar os controles existentes por assunto na estrutura responsiva do fotógrafo.

#### Scenario: Fotógrafo navega entre grupos ou configura a identidade do estúdio

- **WHEN** abre uma seção por atalho, recolhe um grupo ou edita a identidade
- **THEN** a interface preserva rascunhos e destinos existentes, mostra a prévia aplicável e usa os mesmos formulários e controles autorizados

### Requirement: Apresentação do resumo administrativo da Galeria pública

O resumo SHALL usar a estrutura responsiva do fotógrafo e apresentar somente capa, métricas, pastas e clientes autorizadas para a galeria consultada.

#### Scenario: Fotógrafo consulta ou administra a galeria

- **WHEN** consulta capa ou pastas, busca clientes ou abre uma ação de gestão
- **THEN** a interface representa o estado retornado, mantém atalhos e encaminha ações aos fluxos existentes com suas permissões e confirmações

### Requirement: Apresentação da consulta de pedidos da galeria

A consulta SHALL apresentar métricas e snapshots dos pedidos retornados à galeria autorizada. A busca por cliente ou identificador e o filtro por situação SHALL operar sobre esses registros. A tela MUST manter instruções PIX condicionadas ao estado do pedido e encaminhar a confirmação financeira para o fluxo próprio.

#### Scenario: Fotógrafo consulta pedidos de uma galeria

- **WHEN** filtra a lista ou abre o snapshot de um pedido pendente
- **THEN** a tela mantém os totais da galeria, apresenta os registros correspondentes e exibe as instruções PIX somente quando o pedido pendente as fornece

### Requirement: Apresentação da etapa Ajustes da galeria

A primeira etapa SHALL apresentar metadados, situação e modos de acesso do editor autenticado em um layout responsivo.

#### Scenario: Fotógrafo ajusta os dados ou modo de acesso

- **WHEN** altera a identificação, a situação ativa ou o modo de acesso
- **THEN** a interface usa as opções fornecidas, mantém o rascunho diante de erro e avança após o salvamento existente
