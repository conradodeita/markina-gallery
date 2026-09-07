## ADDED Requirements

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
