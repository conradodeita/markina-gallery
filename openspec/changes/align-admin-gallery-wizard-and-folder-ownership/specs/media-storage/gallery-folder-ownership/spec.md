## Purpose

Garantir uma hierarquia inequívoca e auditável entre galerias-mãe, pastas e fotos, impedindo mídia sem contexto e preservando com segurança os registros anteriores à regra.

## ADDED Requirements

### Requirement: Propriedade obrigatória da pasta

O sistema SHALL associar cada pasta a exatamente uma galeria-mãe existente e SHALL NOT aceitar criação, transferência ou persistência de pasta sem essa propriedade.

#### Scenario: Criação dentro da galeria

- **WHEN** o fotógrafo cria uma pasta na etapa Imagens de uma galeria-mãe existente
- **THEN** o sistema vincula a pasta à galeria selecionada e retorna o vínculo confirmado pelo backend

#### Scenario: Tentativa sem galeria

- **WHEN** uma requisição administrativa tenta criar uma pasta sem identificar uma galeria-mãe válida
- **THEN** o sistema recusa a operação sem criar registro parcial

### Requirement: Propriedade obrigatória e coerente da foto

O sistema SHALL associar cada nova foto a exatamente uma pasta e à mesma galeria-mãe proprietária dessa pasta. O sistema SHALL NOT aceitar upload ou cadastro novo de foto diretamente na galeria sem pasta.

#### Scenario: Upload em pasta válida

- **WHEN** o fotógrafo envia uma foto para uma pasta em preparação
- **THEN** o sistema registra a foto na pasta e deriva da pasta a galeria-mãe proprietária

#### Scenario: Vínculos divergentes

- **WHEN** uma operação tenta associar uma foto a uma pasta pertencente a outra galeria-mãe
- **THEN** o sistema recusa a operação e preserva os dois acervos inalterados

#### Scenario: Contrato legado sem pasta

- **WHEN** um consumidor tenta cadastrar uma nova foto diretamente em uma galeria-mãe
- **THEN** o sistema recusa o cadastro e informa que uma pasta em preparação é obrigatória

### Requirement: Saneamento de fotos legadas sem pasta

O sistema SHALL inventariar fotos existentes sem pasta antes de tornar o vínculo obrigatório e SHALL vinculá-las a uma pasta de compatibilidade pertencente à mesma galeria-mãe. O saneamento SHALL preservar identificadores, arquivos, referências privadas, seleções, pedidos, compras e auditoria.

#### Scenario: Galeria com fotos legadas

- **WHEN** a migração encontra uma ou mais fotos sem pasta em uma galeria-mãe
- **THEN** o sistema cria ou reutiliza uma única pasta de compatibilidade nessa galeria e vincula as fotos sem alterar seus identificadores

#### Scenario: Reexecução da migração

- **WHEN** a etapa de saneamento é executada novamente após interrupção ou implantação repetida
- **THEN** o resultado permanece idempotente, sem duplicar pastas nem fotos

#### Scenario: Inconsistência impeditiva

- **WHEN** uma foto legada não possui galeria-mãe válida ou não pode ser vinculada com preservação do histórico
- **THEN** a migração falha de forma explícita antes de aplicar a restrição obrigatória e não apaga o registro

### Requirement: Derivação sem duplicação de mídia

O sistema SHALL disponibilizar às galerias privadas derivadas somente referências autorizadas a fotos liberadas da galeria-mãe. Pastas e arquivos físicos SHALL permanecer pertencentes à galeria-mãe, enquanto seleções, interações, pedidos e histórico SHALL permanecer isolados por responsável conforme suas regras de acesso.

#### Scenario: Liberação para galeria privada

- **WHEN** o fotógrafo libera fotos de uma pasta para uma galeria privada derivada da mesma galeria-mãe
- **THEN** o sistema cria as referências autorizadas sem duplicar o arquivo nem transferir a propriedade da pasta

#### Scenario: Destino de outra galeria-mãe

- **WHEN** o fotógrafo tenta liberar uma pasta para uma galeria privada derivada de outra galeria-mãe
- **THEN** o sistema recusa a liberação e não cria referências cruzadas
