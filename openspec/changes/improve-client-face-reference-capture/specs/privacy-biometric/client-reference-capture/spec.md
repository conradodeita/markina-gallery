# Spec Delta

## Purpose

Define como a cliente obtém e valida temporariamente uma referência facial com detalhe suficiente para pesquisar o índice facial autorizado da galeria.

## ADDED Requirements

### Requirement: Extração da referência preserva os pixels faciais disponíveis
A busca SHALL detectar e alinhar o rosto de referência usando os pixels originais disponíveis dentro de limites operacionais seguros, antes de gerar um embedding compatível com o modelo e versão do índice consultado. SHALL NOT alterar nem reindexar os embeddings do acervo para processar uma referência.

#### Scenario: Referência contém um rosto pequeno detectável
- **WHEN** a cliente envia uma imagem autorizada na qual o rosto ocupa poucos pixels na resolução total
- **THEN** o sistema tenta detectá-lo em escalas adequadas e extrai o recorte alinhado da maior resolução disponível sob os limites configurados

#### Scenario: Referência não contém detalhe suficiente
- **WHEN** o rosto não pode ser detectado ou não atende à qualidade mínima após tentativas de detecção limitadas
- **THEN** a busca termina com estado técnico específico e orienta a cliente a enviar ou capturar outra imagem, sem afirmar que não há fotos dela na galeria

#### Scenario: Busca válida não encontra sugestões
- **WHEN** a referência passa pelas validações técnicas, mas a busca não encontra candidatos confiáveis
- **THEN** a interface informa que não houve sugestões, esclarece que isso não confirma a ausência da pessoa na galeria e oferece nova foto ou seleção manual

### Requirement: Cliente pode escolher upload ou captura guiada
A cliente autenticada e autorizada SHALL poder manter o envio de imagem do dispositivo ou escolher a câmera. Ao escolher a câmera, SHALL concluir uma captura guiada obrigatória com orientação visual e ação explícita de captura; a imagem capturada SHALL passar pelas validações de rosto e qualidade do servidor antes de qualquer comparação com a galeria. A captura guiada SHALL NOT exigir detecção de vivacidade nem impedir busca por referência antiga válida.

#### Scenario: Responsável escolhe foto antiga do dispositivo
- **WHEN** a cliente escolhe uma imagem existente, inclusive antiga, do dispositivo
- **THEN** o sistema mantém o fluxo de upload, aplica os controles de referência e permite pesquisar a galeria autorizada

#### Scenario: Cliente escolhe usar a câmera
- **WHEN** a cliente escolhe usar a câmera
- **THEN** a interface exige uma captura explícita com guia de enquadramento e instruções de pose, iluminação e estabilidade; o servidor valida rosto único e qualidade antes de comparar embeddings com o acervo

#### Scenario: Captura pela câmera não atende à qualidade mínima
- **WHEN** a referência capturada não contém exatamente um rosto utilizável ou falha nos limites de qualidade
- **THEN** nenhuma comparação com o acervo é feita, a interface apresenta a causa sanitizada e orienta nova captura ou permite escolher uma imagem existente

#### Scenario: Pessoa buscada não está presente
- **WHEN** a criança ou outra pessoa procurada não está diante da câmera
- **THEN** o responsável continua podendo usar uma foto existente do dispositivo, sujeito às validações e consentimento vigentes

### Requirement: Consentimento único com declaração condicional de responsabilidade
O diálogo SHALL apresentar um único checkbox obrigatório para qualquer pessoa retratada, sem seletor adulto/menor. A declaração SHALL autorizar em português claro a busca nesta galeria e o tratamento temporário da foto e dos dados biométricos extraídos. Se a pessoa for menor de 18 anos, SHALL declarar que quem aceita é pai, mãe ou responsável legal.

#### Scenario: Referência de pessoa adulta ou menor
- **WHEN** a cliente aceita o checkbox único antes de enviar uma referência
- **THEN** a busca permite o envio após esse aceite, sem inferir a idade da pessoa; se for menor, a declaração aceita inclui responsabilidade legal

#### Scenario: Checkbox não aceito ou declaração antiga
- **WHEN** a cliente desmarca o checkbox ou um pedido novo omite a modalidade condicional
- **THEN** o envio é bloqueado na interface ou recusado pela API, sem criar consulta

### Requirement: Recibo de consentimento condicional preserva histórico
O serviço SHALL registrar a modalidade `conditional` e a versão vigente para novas buscas. SHALL manter os registros históricos `adult` e `minor` sem alteração.

#### Scenario: Nova busca registra a modalidade atual
- **WHEN** a busca é criada com consentimento vigente
- **THEN** o recibo registra `conditional` e a versão aceita

#### Scenario: Registro histórico é consultado
- **WHEN** um recibo antigo usa modalidade `adult` ou `minor`
- **THEN** o sistema preserva seu valor original

### Requirement: Captura guiada prefere a câmera traseira e permite alternância
A captura guiada SHALL solicitar a câmera traseira por padrão e SHALL oferecer alternância para a frontal e de volta quando o navegador suportar seleção de direção. A ação de alternância SHALL encerrar a trilha ativa antes de abrir a outra câmera. A captura explícita e as validações existentes SHALL continuar obrigatórias.

#### Scenario: Cliente abre a câmera guiada
- **WHEN** a cliente escolhe `Usar câmera`
- **THEN** o navegador solicita primeiro `facingMode` `environment` com preferência ideal e a interface continua exigindo o botão de captura explícita

#### Scenario: Cliente alterna a câmera
- **WHEN** a cliente seleciona a ação para trocar a câmera
- **THEN** a trilha atual é encerrada e o navegador solicita a direção oposta; o texto da ação indica qual câmera abrirá

### Requirement: Falha de transporte do envio é explicada sem repetição automática
Quando o navegador rejeitar o envio antes de receber uma resposta HTTP, a interface SHALL substituir mensagens genéricas em inglês por uma orientação em português que informe que o recebimento pode não ter sido confirmado. A interface SHALL NOT repetir automaticamente o upload nem iniciar uma segunda busca.

#### Scenario: Conexão é perdida durante o envio
- **WHEN** `fetch` rejeita sem resposta HTTP durante a criação da busca
- **THEN** a cliente recebe uma mensagem localizada para conferir a conexão e o estado da busca antes de tentar novamente, sem mostrar `Failed to fetch`

#### Scenario: Falha transitória ao atualizar busca já aceita
- **WHEN** uma consulta GET do estado da busca é rejeitada sem resposta ou retorna falha transitória depois que a API aceitou o envio
- **THEN** a interface apresenta orientação localizada e repete somente GET do mesmo UUID em número limitado; após as tentativas automáticas, permite atualização manual pelo mesmo GET, sem criar outra busca ou mostrar `Failed to fetch`

### Requirement: Referência e diagnósticos permanecem minimizados
A melhoria da extração SHALL preservar autorização, consentimento, isolamento da galeria, cifragem, retenção e exclusão da referência já vigentes. Logs, auditoria e métricas SHALL NOT armazenar imagem, recorte facial, embedding, landmarks ou score biométrico.

#### Scenario: Busca termina ou falha
- **WHEN** a extração ou comparação da referência conclui, falha, é cancelada ou expira
- **THEN** a referência temporária segue a política de exclusão existente e apenas estados e métricas técnicas agregadas podem permanecer

### Requirement: Referência prioriza um rosto visualmente dominante
Para a referência de consulta, o processamento SHALL selecionar o maior rosto quando sua confiança for pelo menos 0,85, seu menor lado tiver pelo menos 18% do maior lado da imagem e sua área for pelo menos quatro vezes a de cada outro candidato. A regra SHALL alinhar o recorte selecionado nos pixels originais e SHALL NOT alterar indexação ou similaridade.

#### Scenario: Retrato com pessoas pequenas ao fundo
- **WHEN** um rosto atende a todos os critérios de dominância sobre os demais
- **THEN** apenas ele é alinhado e comparado, sujeito à qualidade mínima vigente

#### Scenario: Faces distintas sem dominância clara
- **WHEN** há mais de um candidato e nenhum atende aos critérios de dominância
- **THEN** a busca termina sem comparação e solicita recorte para isolar um rosto

### Requirement: Detecções repetidas entre escalas são consolidadas
O processamento SHALL consolidar detecções repetidas comparando os cinco landmarks e os centros das caixas no espaço original, com tolerância máxima de 20% do menor lado das caixas, sem exigir IoU mínimo entre escalas.

#### Scenario: Detecção repetida entre escalas com caixas de tamanhos diferentes
- **WHEN** os centros das caixas e todos os landmarks correspondentes de duas detecções estão a até 20% do menor lado das caixas, ainda que o IoU seja inferior a 0,20
- **THEN** o processamento consolida as detecções sem contar o mesmo rosto duas vezes

### Requirement: Confirmação de upload pode ser recuperada sem reenvio
A API SHALL aceitar um UUID v4 opcional da tentativa e reservá-lo antes de qualquer escrita da referência ou retirada de buscas anteriores. A leitura SHALL continuar restrita ao cliente, tenant e galeria autorizados. Após falha de transporte ou resposta inválida, o frontend SHALL consultar exclusivamente esse UUID, SHALL NOT repetir o POST e SHALL oferecer conferência manual se ainda não houver confirmação.

#### Scenario: Resposta se perde após aceitação
- **WHEN** o POST foi aceito mas o navegador não recebeu confirmação válida
- **THEN** um GET autenticado do UUID da tentativa recupera a busca e continua o acompanhamento

#### Scenario: Identificador já existe
- **WHEN** um upload tenta reutilizar um UUID reservado
- **THEN** a API recusa sem sobrescrever referência, criar job duplicado ou retirar buscas existentes

### Requirement: Captura ocupa a tela e textos longos podem ser recolhidos
A câmera guiada SHALL ocupar a viewport, manter o contorno dentro da imagem exibida sem corte oculto, oferecer captura, alternância e saída e encerrar trilhas ao sair. Os detalhes de uso temporário e consentimento SHALL ser recolhíveis. O checkbox único SHALL iniciar marcado, ter resumo visível de autorização e responsabilidade condicional e permitir desmarcação; somente o clique explícito em Autorizar e procurar fotos SHALL enviar e registrar o aceite.

#### Scenario: Abertura sem envio
- **WHEN** a cliente abre o diálogo ou a câmera
- **THEN** nenhum upload ou recibo de consentimento é criado

#### Scenario: Cliente desmarca o aceite
- **WHEN** o checkbox é desmarcado
- **THEN** o envio fica bloqueado até nova seleção explícita do aceite
