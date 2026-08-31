## MODIFIED Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca visual para a cliente autorizada que apresente separadamente todas as Galerias públicas abertas às quais ela está vinculada, suas galerias privadas derivadas ativas e seu histórico comercial. A cliente SHALL poder alternar entre uma Galeria pública autorizada e sua privada correspondente para acrescentar novas seleções enquanto modo, prazo e acesso permitirem, sem acesso administrativo à origem. Uma privada administrativa SHALL permanecer visível com fotos disponíveis mesmo quando possuir zero seleções. A interface SHALL identificar fotos já compradas e preservar pedidos, pagamentos, entregas e evidências visuais permitidas das compras após expiração, encerramento sem referências, desvinculação ou exclusão da galeria operacional.

#### Scenario: Biblioteca vazia

- **WHEN** a cliente autenticada não possui Galeria pública aberta, galeria privada ativa nem entrega histórica
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Nova pasta liberada

- **WHEN** o fotógrafo libera uma nova pasta autorizada para a cliente
- **THEN** a biblioteca ou galeria apresenta a nova rodada separadamente das fotos já revisadas

#### Scenario: Origens e privadas simultâneas

- **WHEN** a cliente possui duas Galerias públicas abertas e galerias privadas derivadas de uma ou ambas
- **THEN** a biblioteca apresenta cada origem e privada com relação visual inequívoca e abre somente os recursos pertencentes à cliente

#### Scenario: Retorno da privada para a origem

- **WHEN** a cliente está em sua galeria privada e deseja escolher fotos adicionais
- **THEN** a interface oferece retorno à Galeria pública correspondente e encaminha cada nova seleção à mesma privada ativa

#### Scenario: Histórico após expiração

- **WHEN** o prazo de seleção de uma galeria privada expira
- **THEN** a cliente continua acessando seus pedidos, entregas e identificação de fotos já compradas, sem poder criar seleção fora das regras de reativação

#### Scenario: Histórico após exclusão da galeria

- **WHEN** o fotógrafo exclui a Galeria pública que originou uma compra confirmada
- **THEN** a cliente continua acessando o registro da compra e sua entrega histórica permitida em um cartão identificado como galeria removida, sem acesso às fotos operacionais não compradas

#### Scenario: Privada permanece após exclusão da origem pública

- **WHEN** o fotógrafo exclui a Galeria pública enquanto a cliente ainda possui fotos disponíveis em uma galeria privada derivada
- **THEN** a biblioteca deixa de apresentar a origem pública, mantém a galeria privada e suas fotos referenciadas para visualização autorizada e impede novas seleções a partir da origem removida

#### Scenario: Histórico após desvinculação

- **WHEN** o fotógrafo desvincula a cliente de uma galeria com compra confirmada
- **THEN** a biblioteca remove a galeria ativa e mantém o histórico comercial e as entregas autorizadas em seção independente

#### Scenario: Histórico após encerramento sem referências

- **WHEN** a cliente remove a última referência disponível de origem `client` depois de uma compra confirmada e a preservação histórica já foi verificada
- **THEN** a biblioteca deixa de mostrar a galeria ativa e mantém a compra e a entrega em seção histórica independente

#### Scenario: Privada administrativa sem seleção

- **WHEN** a cliente possui galeria privada com fotos disponíveis de origem `admin`, mas não selecionou nenhuma
- **THEN** a biblioteca mantém a galeria privada ativa, mostra seleção zerada e não apresenta as fotos disponíveis como escolhidas ou compradas
