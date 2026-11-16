# Spec Delta

## ADDED Requirements

### Requirement: Renomeação de pastas de conteúdo

O fotógrafo autenticado SHALL poder alterar o nome de qualquer pasta comum ou restrita de conteúdo vinculada a uma Galeria pública editável, inclusive após a liberação, e de pastas exclusivas já existentes na administração de uma Galeria privada legada. A operação SHALL rejeitar nomes vazios após normalização e preservar o estado, as fotos, o público e o histórico comercial.

#### Scenario: Renomear pasta comum já liberada

- **WHEN** o fotógrafo altera o nome de uma pasta comum liberada em uma Galeria pública editável
- **THEN** as interfaces administrativas e a próxima consulta da galeria mostram o novo nome sem mudar a liberação, as fotos ou as seleções existentes

#### Scenario: Renomear pasta restrita já liberada

- **WHEN** o fotógrafo altera o nome de uma pasta liberada atribuída a clientes escolhidas
- **THEN** as clientes autorizadas passam a ver o novo nome e as demais continuam sem receber metadados ou acesso à pasta

#### Scenario: Renomear pasta existente em Galeria privada legada

- **WHEN** o fotógrafo altera o nome de uma pasta exclusiva já exibida na tela administrativa de uma Galeria privada legada
- **THEN** a tela mostra o novo nome e conserva as fotos, o estado e o histórico dessa pasta sem criar uma nova galeria ou ampliar o fluxo legado

#### Scenario: Nome ou galeria inválidos para edição

- **WHEN** o fotógrafo envia nome vazio após normalização, mais de 200 caracteres, pasta de outro tenant ou galeria indisponível para edição
- **THEN** o servidor recusa a operação sem alterar nome, público, fotos ou histórico
