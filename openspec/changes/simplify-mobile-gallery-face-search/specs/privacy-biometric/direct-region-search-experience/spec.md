## Purpose

Definir busca direta por rosto já indexado, feedback e retorno aos resultados, distinguindo esse caminho do envio consentido de foto pela cliente e preservando autorização, rastreabilidade e retenção.

## ADDED Requirements

### Requirement: Toque em rosto inicia consulta sem diálogo de consentimento

Ao tocar deliberadamente em uma região facial disponível na galeria autorizada, a cliente SHALL iniciar consulta por essa região sem popup de consentimento, escolha de faixa etária ou checkboxes. A interface SHALL informar imediatamente `Aguarde, procurando fotos…`, evitar admissões duplicadas por toques repetidos e usar percentual somente quando houver progresso real. A operação SHALL comparar apenas o índice autorizado da mesma galeria, sem novo upload, recorte persistido, detector nas prévias, seleção comercial ou concessão de acesso.

#### Scenario: Região válida escolhida
- **WHEN** a cliente autenticada e vinculada toca em um rosto disponível
- **THEN** a busca é admitida diretamente, o estado de espera fica visível mesmo que a página esteja rolada e nenhum diálogo de consentimento é aberto

#### Scenario: Erro ou saturação
- **WHEN** a admissão é recusada ou o job falha
- **THEN** a interface encerra a espera com mensagem sanitizada e ação de nova tentativa apropriada, respeita o prazo de retentativa e preserva a navegação manual

#### Scenario: Toques repetidos ou arraste
- **WHEN** a cliente toca repetidamente durante a admissão, ou arrasta/amplia a imagem
- **THEN** a interface não cria consultas repetidas nem interpreta o gesto de exploração como nova busca

### Requirement: Origem da consulta e auditoria correspondem à ação real

O sistema SHALL distinguir consulta iniciada por região indexada de referência enviada com consentimento explícito. Consulta direta SHALL registrar origem, cliente, galeria, região opaca e versão da política aplicável, sem gerar recibo de consentimento, presumir representação legal ou classificar a pessoa como adulta. Autenticação, vínculo, rollout vigente, disponibilidade da região, compatibilidade do índice, capacidade, rate limit, revogação e retenção SHALL ser repetidos na admissão e execução. A política operacional aprovada SHALL cobrir essa finalidade antes da ativação real; autorização de desenvolvimento SHALL NOT habilitar produção.

#### Scenario: Consulta direta auditada
- **WHEN** o sistema aceita uma busca por região
- **THEN** registra a ação de busca com origem própria, sem registrar aceite de checkbox ou declarar idade que não foi informada

#### Scenario: Região fora do escopo ou revogada
- **WHEN** a região pertence a outra galeria, está removida, ficou incompatível ou perdeu autorização antes do processamento
- **THEN** o sistema nega ou encerra a consulta sem expor dados externos e sem contornar a recusa usando uma prévia recortada

#### Scenario: Referência enviada continua protegida
- **WHEN** uma requisição de upload omite consentimento ou tenta usar o caminho de região para enviar arquivo
- **THEN** o servidor recusa o pedido; a simplificação da busca direta não dispensa controles de upload

### Requirement: Conclusão conduz ao topo uma única vez

Ao concluir com possibilidades a consulta por toque iniciada na página atual, o sistema SHALL fechar o visualizador se aberto, renderizar os resultados na mesma galeria e levar a cliente ao topo da página uma única vez por consulta. SHALL anunciar a conclusão de forma acessível e permitir rolagem e seleção manual das possibilidades. Polling, seleção, mudança de pasta ou restauração de resultado antigo SHALL NOT provocar saltos repetidos.

#### Scenario: Cliente estava no fim da galeria
- **WHEN** a consulta por toque termina com possibilidades enquanto a cliente está abaixo na página
- **THEN** a página vai ao topo após renderizar os resultados e a cliente pode percorrê-los e selecionar fotografias

#### Scenario: Atualização após conclusão
- **WHEN** o mesmo resultado pronto é recebido novamente ou a cliente seleciona uma candidata
- **THEN** a posição de leitura é preservada

#### Scenario: Nenhuma possibilidade
- **WHEN** a consulta termina sem candidatas
- **THEN** a interface informa que nenhuma possibilidade foi encontrada, encerra a espera e mantém o acervo autorizado acessível, sem afirmar que a pessoa não aparece nele

### Requirement: Um único checkbox específico para upload infantil

O envio de foto SHALL manter escolha explícita entre `Pessoa adulta` e `Criança ou adolescente`, origens biblioteca/câmera, aviso de finalidade, limites e retenção. Para menor, SHALL apresentar apenas um checkbox de aceite, inicialmente desmarcado, reunindo declaração de pai/mãe/responsável legal e autorização específica do tratamento temporário para busca naquela galeria. O aviso associado SHALL explicar foto e dados biométricos, sem incluir publicidade ou treinamento. A opção adulta SHALL preservar o consentimento atual. Trocar o tipo de pessoa SHALL limpar o aceite anterior.

#### Scenario: Responsável consente uma única vez
- **WHEN** o upload infantil está disponível e a cliente escolhe menor e uma referência válida
- **THEN** somente o checkbox `Sou pai, mãe ou responsável legal e autorizo a busca de fotos desta criança ou adolescente nesta galeria.` é apresentado para o aceite; o envio permanece bloqueado até sua marcação e segue com o consentimento específico vigente, sem exigir registro prévio de representação

#### Scenario: Cancelamento ou mudança de sujeito
- **WHEN** a cliente cancela, reabre o diálogo ou muda adulto/menor
- **THEN** nenhum aceite anterior é reaproveitado automaticamente nem arquivo enviado sem nova confirmação

### Requirement: Busca infantil autorizada pelo consentimento do responsável

Para novas consultas infantis por upload, o servidor SHALL considerar suficiente a declaração de responsável e o consentimento específico reunidos no checkbox único, sem exigir registro prévio de representação, documento comprobatório ou aprovação administrativa individual. A opção infantil SHALL estar disponível sempre que o serviço de busca por upload estiver tecnicamente disponível para a cliente autenticada e vinculada à galeria. O servidor SHALL validar aceite explícito e versão vigente, registrar cliente, galeria, finalidade, versão e instante UTC e permitir revogação/exclusão sem depender de uma entidade de representação. O sistema SHALL NOT fabricar representação comprovada a partir da autodeclaração. Os demais limites técnicos e de acesso SHALL permanecer iguais aos da busca adulta.

#### Scenario: Responsável sem cadastro prévio consente
- **WHEN** a cliente autenticada e vinculada não possui registro de representação e envia uma referência infantil válida com aceite específico vigente
- **THEN** o servidor admite e executa a busca infantil normalmente, sem pedir documento ou liberação administrativa e sem bloqueá-la pela ausência do registro

#### Scenario: Consentimento ausente ou desatualizado
- **WHEN** uma requisição infantil chega sem aceite explícito ou com versão inválida
- **THEN** o servidor recusa o upload antes do processamento, mesmo que a interface tenha sido contornada

#### Scenario: Responsável revoga a consulta
- **WHEN** a cliente solicita revogação ou exclusão de sua busca infantil autorizada por consentimento
- **THEN** novas etapas dessa consulta são interrompidas e seus temporários e resultados são eliminados conforme o procedimento de direitos, sem exigir identificação de registro de representação

#### Scenario: Registro histórico de representação
- **WHEN** uma consulta anterior já possui representação vinculada
- **THEN** a evidência e os controles de revogação históricos são preservados; novas consultas usam a autorização por consentimento, sem exigir nem criar representação retroativa
