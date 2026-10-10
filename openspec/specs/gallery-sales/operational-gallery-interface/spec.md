# operational-gallery-interface Specification

## Purpose

Permitir ao fotógrafo operar a galeria única, seus clientes e pastas pela interface, sem expor acervos não autorizados ou exigir chamadas técnicas.

## Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface para criar e operar uma galeria por evento, seus clientes, pastas e JPEGs, com público comum ou restrito por pasta. A interface SHALL apresentar fluxo claro de criação, edição, preparação e liberação, sem criar galeria derivada nem expor acervo antes da autorização e liberação aplicáveis.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo com dados válidos
- **THEN** o sistema cria somente a galeria e suas pastas necessárias, com confirmação ou erro acessível, sem derivada automática

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo vincula outra responsável à mesma galeria
- **THEN** a responsável vê pastas comuns e as atribuídas a ela, com seleção, prazo, pedidos e histórico independentes

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta ainda não liberada
- **THEN** ele vê JPEGs, processamento, público pretendido e ações administrativas; nenhuma cliente vê a pasta

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a galeria
- **THEN** não vê controles administrativos nem pastas ou fotos fora de sua autorização

### Requirement: Estados operacionais claros

O sistema SHALL apresentar estados de carregamento, vazio, erro, preparação, progresso, sucesso, bloqueio e expiração nas telas administrativas e da cliente, com linguagem compreensível e ação de recuperação quando aplicável.

#### Scenario: Importação em processamento

- **WHEN** um JPEG foi aceito e seus derivados ainda estão sendo preparados
- **THEN** o fotógrafo vê o estado pendente sem receber URL do original

#### Scenario: Liberação concluída

- **WHEN** o fotógrafo conclui a liberação de uma pasta
- **THEN** a interface confirma o público efetivo retornado pelo backend e as clientes alcançadas, sem sugerir atualização de galerias derivadas

### Requirement: Interface orientada pelo backend

O sistema SHALL obter dados, permissões, disponibilidade e resultados de ações administrativas exclusivamente de APIs autenticadas do backend. A interface SHALL NOT criar autorização, registros, progresso de upload ou liberação simulados no browser.

#### Scenario: Estado administrativo

- **WHEN** o fotógrafo abre ou altera uma tela operacional
- **THEN** a interface consulta o backend e apresenta o estado retornado, sem criar autorização ou registros simulados no browser

#### Scenario: Consulta por responsável

- **WHEN** o fotógrafo busca por nome ou telefone na ficha de uma galeria-fonte
- **THEN** o sistema retorna apenas os vínculos e estados autorizados da consulta e permite abrir a ficha individual da seleção

### Requirement: Exclusão segura de galeria privada

O sistema SHALL permitir exclusão operacional de galeria ou pasta somente se os vínculos, mídias e registros comerciais protegidos permitirem. Uma compra confirmada SHALL bloquear remoção que apagaria o histórico; bloqueio ou congelamento de acesso SHALL permanecer disponível conforme a regra comercial.

#### Scenario: Histórico de compra preservado

- **WHEN** o fotógrafo tenta excluir uma galeria ou pasta com foto de pedido confirmado
- **THEN** o backend recusa a exclusão e preserva o pedido e seus snapshots

### Requirement: Acervo da cliente no card da Galeria pública

Na etapa Clientes da Galeria pública, cada card SHALL oferecer uma seção inicialmente recolhida intitulada `Acervo da cliente`, com criação de pasta restrita, upload de JPEGs, atribuição de outras clientes, pastas, fotos e estados individuais retornados pelo backend. Abrir ou recolher a seção SHALL alterar somente o estado de apresentação. A pasta criada no card SHALL ser inicialmente atribuída àquela cliente e continuar única quando compartilhada. Pastas comuns SHALL permanecer na etapa Imagens. A interface SHALL NOT oferecer criação, clonagem ou abertura de galeria privada derivada.

#### Scenario: Fotógrafo abre o card

- **WHEN** o fotógrafo expande `Acervo da cliente` no card de uma cliente
- **THEN** vê o acervo, pode criar pasta restrita e enviar fotos naquele contexto, sem navegar para uma galeria privada

#### Scenario: Pasta compartilhada por dois cards

- **WHEN** o fotógrafo adiciona outra cliente à pasta restrita criada em um card
- **THEN** ambos os cards mostram a mesma pasta, sem duplicar fotos ou reiniciar seleções e pedidos individuais

### Requirement: Navegação global de clientes

O sistema SHALL apresentar `Clientes` como destino próprio da navegação administrativa, sem depender do contexto ou da existência de uma galeria. A etapa Clientes de uma Galeria pública SHALL reutilizar o mesmo cadastro global e acrescentar somente ações e estados específicos do vínculo atual.

#### Scenario: Diretório e etapa usam a mesma identidade

- **WHEN** o fotógrafo edita uma cliente no diretório global e depois abre a etapa 05
- **THEN** a etapa apresenta o mesmo cadastro atualizado, inclusive quando já vinculado, sem criar ou manter uma cópia local

### Requirement: PIX global na etapa Vendas

O sistema SHALL remover da etapa Vendas a edição de chave, BR Code, recebedor, cidade e instruções PIX por galeria. A etapa SHALL consultar o contrato global e apresentar seu estado, prévia e destino de correção antes de salvar e avançar.

#### Scenario: Fotógrafo avança na etapa 02

- **WHEN** o fotógrafo salva preço e demais regras comerciais da galeria
- **THEN** o sistema persiste somente esses dados por galeria e mantém a configuração PIX sob o contrato global

### Requirement: Cards de clientes vinculadas por atividade

O sistema SHALL apresentar os cards de clientes vinculadas a uma Galeria pública em uma única coluna e ordená-los pela atividade de acesso mais recente primeiro. A ordem SHALL usar a última visualização de prévia protegida registrada para a Galeria pública ou galeria privada correspondente e, quando inexistente, a data de criação do vínculo. O menu recolhível e os demais controles existentes SHALL permanecer disponíveis.

#### Scenario: Cliente retorna à galeria

- **WHEN** uma cliente visualiza uma prévia protegida depois das demais clientes
- **THEN** seu card aparece no topo após a próxima consulta à lista

#### Scenario: Cliente ainda não abriu prévias

- **WHEN** não há visualização protegida registrada para uma cliente vinculada
- **THEN** o sistema ordena seu card pela data de criação do vínculo, mantendo clientes sem data no final

#### Scenario: Lista em telas largas

- **WHEN** o fotógrafo consulta clientes vinculadas em uma tela larga
- **THEN** cada card ocupa uma linha e mantém o menu recolhível e os demais controles
