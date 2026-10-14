# gallery-sales/client-selection-operations Specification

## ADDED Requirements

### Requirement: Ficha visual portátil da seleção

O sistema SHALL permitir ao fotógrafo baixar os itens dos pedidos confirmados da cliente naquela galeria em um único arquivo HTML autônomo, sem expor originais, URLs autenticadas ou dados de outras clientes. O arquivo SHALL conter data e hora de geração, nome da galeria, nome da cliente, prévias históricas ou administrativas disponíveis em grade e o nome congelado de cada foto abaixo da respectiva prévia. Uma seleção ainda não comprada SHALL NOT entrar no relatório.

#### Scenario: Baixar seleção com prévias

- **WHEN** o fotógrafo aciona “Baixar seleção individual” para uma cliente com compra confirmada
- **THEN** o navegador recebe um HTML para salvar no dispositivo, com as fotos compradas, nomes e metadados da geração

#### Scenario: Arquivo autônomo

- **WHEN** o fotógrafo abre o HTML baixado sem conexão com o sistema
- **THEN** as prévias embutidas continuam visíveis e o sistema não depende de arquivo gerado ou mantido no servidor

#### Scenario: Prévia indisponível

- **WHEN** uma foto selecionada ainda não possui prévia administrativa pronta
- **THEN** o HTML identifica a foto e informa a indisponibilidade sem usar o original como fallback

#### Scenario: Nenhuma compra confirmada

- **WHEN** a cliente ainda não tem pedido confirmado nessa galeria
- **THEN** a interface informa que o download estará disponível após a primeira compra e a API recusa gerar um arquivo vazio
