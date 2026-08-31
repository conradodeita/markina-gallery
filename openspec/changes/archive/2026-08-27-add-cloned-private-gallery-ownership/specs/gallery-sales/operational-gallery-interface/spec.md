## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado telas para criar cliente, acervo-fonte não listado, registrar/importar JPEG e criar galerias privadas derivadas com fotos, prazo, mensagem e permissões. O fotógrafo SHALL poder criar galerias independentes para responsáveis diferentes a partir do mesmo acervo-fonte, sem expor o acervo coletivo nem duplicar mídia.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo administrativo com dados válidos
- **THEN** o sistema cria somente as referências privadas escolhidas e apresenta confirmação ou erro acessível

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo vincula uma nova responsável a fotos já disponibilizadas para outra responsável
- **THEN** o sistema cria ou vincula uma galeria privada independente para a nova responsável sem alterar seleção, prazo, pedido ou histórico da primeira

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora de sua galeria derivada

### Requirement: Interface orientada pelo backend

O sistema SHALL obter dados, propriedade, disponibilidade e resultados de ações administrativas exclusivamente de APIs autenticadas do backend. A ficha de uma galeria-fonte SHALL listar clientes vinculadas e resumir o estado individual de cada galeria privada derivada, sem o frontend criar autorização ou registros simulados no browser.

#### Scenario: Estado administrativo

- **WHEN** o fotógrafo abre ou altera uma tela operacional
- **THEN** a interface consulta o backend e apresenta o estado retornado, sem criar autorização ou registros simulados no browser

#### Scenario: Consulta por responsável

- **WHEN** o fotógrafo busca por nome ou telefone na ficha de uma galeria-fonte
- **THEN** o sistema retorna apenas os vínculos e estados autorizados da consulta e permite abrir a ficha individual da seleção
