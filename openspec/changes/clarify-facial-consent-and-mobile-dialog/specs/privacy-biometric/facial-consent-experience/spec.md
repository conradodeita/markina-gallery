## Purpose

Definir uma experiência clara, específica e responsiva para a cliente compreender e autorizar o tratamento temporário da referência facial antes de iniciar uma busca restrita a uma galeria.

## ADDED Requirements

### Requirement: Aviso específico descreve o tratamento facial real

Antes do envio, o sistema SHALL apresentar aviso destacado e separado dos termos gerais informando que a foto escolhida e a representação biométrica extraída serão usadas temporariamente apenas para procurar possíveis correspondências na galeria atual. O aviso SHALL informar os prazos efetivos de eliminação da referência e expiração dos resultados, SHALL esclarecer que não há cadastro biométrico permanente e SHALL NOT afirmar que a imagem nunca passa por armazenamento temporário durante o processamento.

#### Scenario: Cliente consulta finalidade e retenção
- **WHEN** a cliente abre o diálogo de busca facial
- **THEN** ela visualiza a finalidade restrita à galeria, o prazo máximo da referência, o prazo dos resultados e a informação de eliminação automática antes de selecionar ou enviar um arquivo

### Requirement: Limitações e alternativa manual permanecem explícitas

O diálogo SHALL informar que as correspondências são sugestões, não confirmam identidade e podem conter resultados incorretos. O sistema SHALL informar que a busca é opcional e que recusar ou cancelar o consentimento não remove a navegação e a seleção manual já autorizadas.

#### Scenario: Cliente decide não consentir
- **WHEN** a cliente fecha ou cancela o diálogo sem marcar o consentimento
- **THEN** nenhuma referência é enviada e a galeria continua disponível para busca e seleção manual

### Requirement: Consentimento infantil destacado e comprovável

Quando a referência for declarada como pertencente a criança ou adolescente e o backend informar que o fluxo infantil está disponível, o sistema SHALL exigir confirmação explícita de que a cliente é pai, mãe ou responsável legal e consentimento específico para o tratamento temporário da foto e dos dados biométricos naquela galeria. O controle SHALL iniciar desmarcado, SHALL NOT ser agrupado com autorização para publicidade, treinamento ou outra finalidade e SHALL continuar subordinado à representação legal válida exigida pelo backend.

#### Scenario: Responsável autoriza a busca infantil
- **WHEN** a cliente seleciona `Criança ou adolescente`, possui representação vigente, escolhe uma referência válida e marca a confirmação específica
- **THEN** a ação de iniciar a busca é habilitada com a versão vigente do consentimento sem ampliar o escopo além da galeria atual

#### Scenario: Confirmação infantil ausente
- **WHEN** a cliente seleciona `Criança ou adolescente` e não confirma ser responsável legal
- **THEN** o sistema mantém a ação de iniciar desabilitada e não envia a referência

### Requirement: Orientação segura para uma referência adequada

O sistema SHALL recomendar uma foto semelhante a foto de documento quanto a enquadramento — frontal, nítida, bem iluminada, com o rosto inteiro e apenas uma pessoa — para aumentar a chance técnica de correspondência. A orientação SHALL deixar claro que não é necessário fotografar nem enviar documento de identidade e SHALL NOT solicitar nome, número de documento ou outro dado adicional.

#### Scenario: Cliente escolhe a referência
- **WHEN** a cliente chega à etapa de seleção da foto
- **THEN** a interface apresenta a recomendação de enquadramento e esclarece que somente a foto do rosto é necessária, sem documento oficial

### Requirement: Diálogo utilizável em viewport mobile

O diálogo SHALL permanecer inteiramente operável em smartphone, respeitando a altura útil dinâmica da viewport, permitindo rolagem interna quando necessário e mantendo título, campos, mensagens, checkboxes e ações sem corte ou sobreposição. As ações SHALL possuir alvos de toque legíveis e o fechamento SHALL continuar disponível por ação explícita e pela tecla aplicável.

#### Scenario: Smartphone com altura reduzida
- **WHEN** a cliente abre o diálogo em viewport mobile com altura reduzida
- **THEN** ela consegue rolar por todo o aviso, selecionar a origem e o tipo de pessoa, marcar o consentimento e alcançar os botões sem conteúdo oculto atrás da interface do navegador

#### Scenario: Mensagem de erro no mobile
- **WHEN** uma validação de arquivo exibe erro dentro do diálogo em smartphone
- **THEN** a mensagem participa do fluxo rolável sem cobrir os controles nem deslocar as ações para fora de uma área alcançável
