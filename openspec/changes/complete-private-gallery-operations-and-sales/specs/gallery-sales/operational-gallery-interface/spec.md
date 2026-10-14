## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface original para criar e operar clientes, Galerias públicas, galerias privadas, pastas e JPEGs. A interface SHALL permitir criar uma privada para clientes autorizados e montar seu acervo administrativo somente com novos JPEGs enviados do dispositivo diretamente para pastas daquela privada. A interface e as APIs administrativas SHALL NOT oferecer nem aceitar inclusão manual de fotos já existentes em Galeria pública ou em outra privada, nem atalhos para carregar JPEGs na pública dentro da ficha privada.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo cria uma galeria privada e carrega JPEGs válidos do dispositivo
- **THEN** o sistema cria pastas e fotos exclusivas da privada e apresenta processamento, confirmação ou erro acessível

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo cria outra galeria privada para uma nova cliente
- **THEN** o sistema exige novos uploads próprios ou permite a privada vazia, sem reutilizar fotos de qualquer galeria e sem alterar seleção, prazo, pedido ou histórico da primeira

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta privada ainda em processamento
- **THEN** ele vê os JPEGs, o estado real e as ações permitidas somente no contexto daquela privada

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora das galerias e pastas autorizadas para sua identidade

#### Scenario: Controles públicos removidos da privada

- **WHEN** o fotógrafo abre a ficha de uma galeria privada
- **THEN** a interface não apresenta `Adicionar fotos da Galeria pública`, `Adicionar ao acervo privado` ou `Carregar novos JPEGs na pública`

#### Scenario: Tentativa administrativa por API legada

- **WHEN** uma chamada administrativa tenta criar, adicionar ou clonar referências de fotos já existentes para uma galeria privada
- **THEN** o backend recusa a gravação sem alterar a privada, a seleção da cliente ou os arquivos existentes

#### Scenario: Seleção automática da cliente preservada

- **WHEN** a cliente seleciona uma foto autorizada na Galeria pública
- **THEN** o backend cria ou atualiza automaticamente a privada correspondente e registra a seleção sem exigir upload administrativo

## ADDED Requirements

### Requirement: Métricas administrativas autoritativas

O sistema SHALL calcular no backend e apresentar de forma atualizável `Fotos no acervo privado`, `Fotos selecionadas` e `Fotos compradas` por cliente e galeria, sem inferência ou cache persistente no navegador.

#### Scenario: Cliente seleciona duas fotos

- **WHEN** duas seleções persistidas pertencem à cliente naquela galeria
- **THEN** os cards da Galeria pública e privada apresentam `2` em `Fotos selecionadas` após nova consulta ao backend

#### Scenario: Pedido confirmado ou corrigido

- **WHEN** um pedido muda entre confirmação e correção
- **THEN** a contagem de fotos compradas e os estados comerciais refletem a transição sem combinar outra galeria ou cliente
