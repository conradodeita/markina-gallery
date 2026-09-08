## Purpose

Permitir ao fotógrafo revisar e organizar com segurança as fotos de uma pasta vinculada à galeria, sem expor originais, conteúdo de terceiros ou fotos protegidas por histórico comercial.

## ADDED Requirements

### Requirement: Revisão contextual de pasta e prévias protegidas

O sistema SHALL permitir ao fotógrafo abrir uma pasta da galeria-mãe atual e SHALL apresentar sua contagem, estado de processamento e prévias com marca d’água. A visualização ampliada SHALL reutilizar somente uma prévia administrativa protegida e SHALL NOT retornar o arquivo original.

#### Scenario: Pasta com fotos processadas

- **WHEN** o fotógrafo abre uma pasta que contém JPEGs processados
- **THEN** o sistema mostra a contagem da pasta e uma grade de prévias protegidas que podem ser ampliadas sem expor o original

#### Scenario: Foto ainda em processamento

- **WHEN** o fotógrafo abre uma pasta com foto cujo derivado ainda não foi concluído
- **THEN** o sistema mostra o estado pendente da foto sem apresentar uma URL de origem ou uma prévia inexistente

### Requirement: Exclusão segura de foto administrativa

O sistema SHALL permitir que o fotógrafo exclua uma foto somente quando ela pertence à pasta e à galeria-mãe atuais e não possui compra confirmada. A exclusão SHALL remover referências administrativas permitidas, arquivo-fonte e derivados associados, sem afetar outras fotos ou galerias.

#### Scenario: Exclusão antes de compra

- **WHEN** o fotógrafo confirma a exclusão de uma foto sem compra confirmada
- **THEN** o sistema exclui a foto e atualiza a contagem e as prévias da pasta

#### Scenario: Foto com compra confirmada

- **WHEN** o fotógrafo tenta excluir uma foto que integra um pedido com pagamento confirmado
- **THEN** o sistema recusa a exclusão, preserva a foto e informa o motivo de forma clara

#### Scenario: Foto de outra galeria ou pasta

- **WHEN** o fotógrafo tenta excluir uma foto fora do contexto da galeria e pasta abertas
- **THEN** o sistema recusa a operação sem alterar qualquer registro

### Requirement: Capa administrativa da galeria-mãe

O sistema SHALL permitir ao fotógrafo escolher ou trocar a capa de uma galeria-mãe entre fotos pertencentes a ela. Quando não houver escolha explícita, o sistema SHALL usar a primeira foto disponível apenas como prévia padrão, sem alterar a propriedade da foto.

#### Scenario: Escolha de capa

- **WHEN** o fotógrafo define uma foto processada da galeria como capa
- **THEN** o resumo e a lista administrativa exibem sua prévia protegida como capa da galeria

#### Scenario: Capa removida

- **WHEN** o fotógrafo exclui a foto usada como capa e a exclusão é permitida
- **THEN** o sistema remove a escolha de capa e volta a aplicar a prévia padrão disponível, se existir

### Requirement: Pastas exclusivamente contextuais

O sistema SHALL criar e listar pastas somente no contexto explícito de uma galeria-mãe. A contagem e a prévia de cada pasta SHALL refletir apenas fotos pertencentes àquela pasta.

#### Scenario: Duas pastas na mesma galeria

- **WHEN** o fotógrafo cria duas pastas e envia fotos somente para a primeira
- **THEN** a primeira mostra sua contagem e prévia, enquanto a segunda permanece vazia e administrativa
