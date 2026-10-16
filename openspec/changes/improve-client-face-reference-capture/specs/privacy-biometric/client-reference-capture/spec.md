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
O diálogo de envio SHALL apresentar um único checkbox obrigatório para qualquer pessoa retratada, sem seletor adulto/menor. O texto SHALL autorizar de forma livre, informada e específica a busca nesta galeria e o tratamento temporário da foto e dos dados biométricos extraídos; SHALL declarar que, se a pessoa retratada for menor de 18 anos, a pessoa que aceita é pai, mãe ou responsável legal. A interface SHALL apresentar a declaração em português claro, registrar a modalidade `conditional` e manter registros históricos `adult` e `minor` sem alteração. O serviço SHALL exigir o checkbox aceito e a versão de consentimento vigente para toda nova busca por upload.

#### Scenario: Referência de pessoa adulta ou menor
- **WHEN** a cliente aceita o checkbox único antes de enviar uma referência
- **THEN** a busca registra o consentimento específico na versão vigente e a modalidade condicional, sem inferir ou registrar idade; se a pessoa for menor, a declaração aceita inclui responsabilidade legal

#### Scenario: Checkbox não aceito ou declaração antiga
- **WHEN** a cliente não marca o checkbox ou um pedido novo omite a modalidade condicional
- **THEN** o envio é bloqueado na interface ou recusado pela API, sem criar consulta

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

### Requirement: Referência e diagnósticos permanecem minimizados
A melhoria da extração SHALL preservar autorização, consentimento, isolamento da galeria, cifragem, retenção e exclusão da referência já vigentes. Logs, auditoria e métricas SHALL NOT armazenar imagem, recorte facial, embedding, landmarks ou score biométrico.

#### Scenario: Busca termina ou falha
- **WHEN** a extração ou comparação da referência conclui, falha, é cancelada ou expira
- **THEN** a referência temporária segue a política de exclusão existente e apenas estados e métricas técnicas agregadas podem permanecer
