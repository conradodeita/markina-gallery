## Purpose

Permitir ao fotógrafo operar galerias privadas pela interface, sem expor acervos ou exigir chamadas técnicas.

## ADDED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado telas para criar cliente, acervo-mãe, registrar/importar JPEG e criar galeria derivada com fotos, prazo, mensagem e permissões.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo administrativo com dados válidos
- **THEN** o sistema cria somente as referências privadas escolhidas e apresenta confirmação ou erro acessível

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora de sua galeria derivada

### Requirement: Estados operacionais claros

O sistema SHALL apresentar estados de carregamento, vazio, erro e sucesso nas telas administrativas e do cliente.

#### Scenario: Importação em processamento

- **WHEN** um JPEG foi aceito e seus derivados ainda estão sendo preparados
- **THEN** o fotógrafo vê o estado pendente sem receber URL do original

### Requirement: Interface orientada pelo backend

O sistema SHALL obter dados, permissões, disponibilidade e resultados de ações administrativas exclusivamente de APIs autenticadas do backend.

#### Scenario: Estado administrativo

- **WHEN** o fotógrafo abre ou altera uma tela operacional
- **THEN** a interface consulta o backend e apresenta o estado retornado, sem criar autorização ou registros simulados no browser
