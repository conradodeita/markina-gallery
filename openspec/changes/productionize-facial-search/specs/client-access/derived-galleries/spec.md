## ADDED Requirements

### Requirement: Busca facial não concede acesso nem cria galeria privada

A busca facial SHALL funcionar apenas dentro de uma Galeria pública já autorizada para a cliente e SHALL retornar candidatas como uma visualização opcional do mesmo acervo. A criação ou reutilização da galeria privada, da referência de foto selecionada e da cotação SHALL ocorrer somente quando a cliente escolher explicitamente uma candidata pela mutation de seleção existente.

#### Scenario: Consulta concluída sem seleção

- **WHEN** a busca facial retorna candidatas e a cliente não seleciona nenhuma foto
- **THEN** o sistema cria zero galerias privadas, memberships, seleções, pedidos e pagamentos em nome da cliente

#### Scenario: Primeira candidata selecionada

- **WHEN** a cliente seleciona explicitamente uma candidata válida
- **THEN** o sistema cria ou reutiliza exatamente uma galeria privada para o par Galeria pública + cliente e atualiza a mesma seleção e cotação usadas no fluxo manual

#### Scenario: Vínculo removido durante a consulta

- **WHEN** o vínculo da cliente com a Galeria pública é removido antes da leitura ou seleção da candidata
- **THEN** o backend recusa a operação sem revelar metadados da foto e elimina os temporários e resultados ainda retidos
