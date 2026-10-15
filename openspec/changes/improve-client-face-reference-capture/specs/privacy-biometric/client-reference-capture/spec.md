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

### Requirement: Referência e diagnósticos permanecem minimizados
A melhoria da extração SHALL preservar autorização, consentimento, isolamento da galeria, cifragem, retenção e exclusão da referência já vigentes. Logs, auditoria e métricas SHALL NOT armazenar imagem, recorte facial, embedding, landmarks ou score biométrico.

#### Scenario: Busca termina ou falha
- **WHEN** a extração ou comparação da referência conclui, falha, é cancelada ou expira
- **THEN** a referência temporária segue a política de exclusão existente e apenas estados e métricas técnicas agregadas podem permanecer
