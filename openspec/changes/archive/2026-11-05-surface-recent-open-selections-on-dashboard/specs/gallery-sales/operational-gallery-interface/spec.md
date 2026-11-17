## ADDED Requirements

### Requirement: Clientes com seleção atual na Visão geral
A Visão geral SHALL apresentar até cinco grupos de seleção atual do tenant autenticado, com cliente, Galeria pública, quantidade de fotos e o instante em que o carrinho atual começou. Os grupos SHALL ser ordenados pela atividade de seleção mais recente, e o card SHALL preservar os atalhos de galerias recentes.

#### Scenario: Cliente inicia uma seleção
- **WHEN** uma cliente autorizada seleciona fotos em uma Galeria pública
- **THEN** a próxima consulta da Visão geral pode apresentar o grupo dessa cliente, com a quantidade atual e o instante em que a primeira foto da seleção atual foi escolhida

#### Scenario: Remover a primeira foto escolhida
- **WHEN** a cliente remove a primeira foto que escolheu, mas mantém outras fotos no carrinho
- **THEN** o horário de início permanece o instante em que a seleção atual começou

#### Scenario: Ordenar atividade recente
- **WHEN** há mais de cinco grupos com fotos selecionadas
- **THEN** a Visão geral apresenta os cinco grupos com adição de foto mais recente, identificando o início de cada seleção atual

#### Scenario: Seleção de outro tenant
- **WHEN** uma cliente de outro tenant tem fotos selecionadas
- **THEN** a Visão geral atual não revela seu nome, galeria, quantidade ou horário

#### Scenario: Nenhum grupo atual
- **WHEN** nenhuma foto permanece selecionada em qualquer grupo do tenant
- **THEN** a interface apresenta um estado vazio sem inventar cliente ou atividade histórica

### Requirement: Horário sem registro do carrinho atual
Se o horário exato não estiver registrado, a interface SHALL mostrar `Horário não registrado` e não SHALL estimar o início pelas fotos que restaram.

#### Scenario: Carrinho sem início registrado
- **WHEN** há uma seleção atual sem horário exato registrado
- **THEN** a interface mantém cliente e galeria visíveis e informa `Horário não registrado`, sem estimar o início

### Requirement: Fuso horário visível do horário da seleção
O backend SHALL manter e retornar o instante da seleção em UTC. Como não há fuso configurável por tenant, a Visão geral SHALL exibir a hora convertida para o fuso local do dispositivo e identificar essa regra na interface.

#### Scenario: Apresentar o horário registrado
- **WHEN** a Visão geral apresenta um início exato de seleção
- **THEN** a interface converte o instante UTC para o fuso do dispositivo e informa que os horários seguem esse fuso
