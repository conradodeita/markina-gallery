## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface original para criar e operar clientes, acervos-fonte não listados, galerias privadas, pastas e JPEGs. A interface SHALL apresentar fluxo claro de criação, edição, preparação e liberação, sem expor acervos a clientes antes da autorização e liberação aplicáveis.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo administrativo com dados válidos
- **THEN** o sistema cria somente as referências privadas escolhidas e apresenta confirmação ou erro acessível

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta ainda não liberada
- **THEN** ele vê os JPEGs, o estado de processamento e as ações de edição ou liberação disponíveis somente para ele

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora de sua galeria derivada e pastas liberadas

### Requirement: Estados operacionais claros

O sistema SHALL apresentar estados de carregamento, vazio, erro, preparação, progresso, sucesso, bloqueio e expiração nas telas administrativas e da cliente, com linguagem compreensível e ação de recuperação quando aplicável.

#### Scenario: Importação em processamento

- **WHEN** um JPEG foi aceito e seus derivados ainda estão sendo preparados
- **THEN** o fotógrafo vê o estado pendente sem receber URL do original

#### Scenario: Liberação concluída

- **WHEN** o fotógrafo conclui a liberação de uma pasta
- **THEN** a interface confirma o resultado retornado pelo backend e informa quais galerias privadas foram atualizadas

### Requirement: Interface orientada pelo backend

O sistema SHALL obter dados, permissões, disponibilidade e resultados de ações administrativas exclusivamente de APIs autenticadas do backend. A interface SHALL NOT criar autorização, registros, progresso de upload ou liberação simulados no browser.

#### Scenario: Estado administrativo

- **WHEN** o fotógrafo abre ou altera uma tela operacional
- **THEN** a interface consulta o backend e apresenta o estado retornado, sem criar autorização ou registros simulados no browser

### Requirement: Exclusão segura de galeria privada
O sistema SHALL disponibilizar exclusão somente quando a galeria não tiver fotos, seleções ou pedidos. Galeria com compra confirmada SHALL ser preservada, podendo apenas ser congelada ou bloqueada.

#### Scenario: Histórico de compra preservado
- **WHEN** o fotógrafo tenta excluir uma galeria com pedido confirmado
- **THEN** o backend recusa a exclusão e a interface oferece congelar ou bloquear acesso
